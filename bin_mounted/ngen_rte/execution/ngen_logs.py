"""Live polling of ngen log files"""

import functools
import os
import time
import traceback
from pathlib import Path

import ewts
import ngen_rte.consts as c
from ewts import EwtsLogger, LogParts, get_logger, parts_of_log_line
from mswm.build_inputs import RealizationBuilder
from ngen_rte.configs import (
    RTEBaseConfig,
    RTECalibConfig,
    RTEDefaultConfig,
    RTEForecastConfig,
    RTETestConfig,
)
from pydantic import BaseModel, ConfigDict, Field

print = functools.partial(print, flush=True)


THROTTLE_SECONDS = 3


class _LogParserBase(BaseModel):
    """Parser for log files."""

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    tolerant: bool = False
    """Passed on to ``ewts.parts_of_log_line()`` to control whether parsing errors are tolerated or raise exceptions."""

    log_lines_hash_cache: dict[int | None, set[int]] = Field(
        default_factory=dict, init=False
    )
    """Used to track signatures (raw hashes) of log lines already found.
    Dictionary keyed on MPI rank, with each value being a set of hashes of log lines found for that rank.
    If the MPI rank concept does not apply, use None as the key."""

    def model_post_init(self, __context) -> None:
        self.__throttle_last_time = None

    def _line_is_new(self, mpi_rank: int | None, line: str) -> bool:
        """Hash the log line and store the hash in a dict keyed on mpi_rank.
        Return True if the hash has been seen already for that rank, otherwise return False.
        If the log file is not associated with MPI, use None for mpi_rank."""
        h = hash((mpi_rank, line))
        self.log_lines_hash_cache.setdefault(mpi_rank, set())
        s = self.log_lines_hash_cache[mpi_rank]
        if h in s:
            return False
        else:
            s.add(h)
            return True

    def _iter_log_paths(self):
        """Yields (mpi_rank, log_file_path) tuples for each log file path to read from.
        Behavior is dynamic based on the child instance type of self."""
        if isinstance(self, _LogParserNgen):
            for mpi_rank in range(self.cfg.nprocs):
                if (
                    self.parse_only_rank is not None
                    and mpi_rank != self.parse_only_rank
                ):
                    continue
                ngen_log_path = self.ngen_log_path(mpi_rank)
                yield mpi_rank, ngen_log_path
        elif isinstance(self, _LogParserGeneric):
            yield None, self.log_file_path
        else:
            raise TypeError(f"Unsupported log parser type: {type(self)}")

    def __throttle(self) -> None:
        """Throttle to avoid reading log files too quickly."""
        if self.__throttle_last_time is None:
            self.__throttle_last_time = 0.0
        now = time.perf_counter()
        if now - self.__throttle_last_time < THROTTLE_SECONDS:
            time.sleep(THROTTLE_SECONDS - (now - self.__throttle_last_time))
        self.__throttle_last_time = time.perf_counter()

    def _new_log_parts(self) -> list[tuple[int, LogParts, Path | str]]:
        """Returns (rank, LogParts, log_file) tuples for each *new* message extracted from the ngen log files.
        Note that currently this reads the entire file, so a throttle has been added so that
        it does not get called too frequently. This could be optimized to keep the file handle open and
        yield lines only as they arrive into the file, but this change might introduce risks and complexity."""
        self.__throttle()
        result: list[tuple[int, LogParts, Path | str]] = []
        for mpi_rank, log_file_path in self._iter_log_paths():
            # TODO move everyting below into another method and try/except on FileNotFoundError
            if not os.path.exists(log_file_path):
                print(f"Warning: ngen log file does not exist: {log_file_path}")
                continue
            print(f"Reading: {log_file_path}")
            with open(log_file_path) as f:
                for line in f:
                    if not self._line_is_new(mpi_rank, line):
                        continue
                    line = line.rstrip()
                    try:
                        parts = parts_of_log_line(line, tolerant=self.tolerant)
                    except Exception as e:
                        print(
                            f"Error parsing line into parts: {line}. Error: {e}. Traceback: {traceback.format_exc()}"
                        )
                        continue
                    result.append((mpi_rank, parts, log_file_path))
        return result


class _LogParserNgen(_LogParserBase):
    """Parser for ngen log files with MPI awareness."""

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    cfg: RTEBaseConfig
    rb: RealizationBuilder
    parse_only_rank: int | None
    """Only used by child class _LogParserNgen, where one component may have multiple logs (one for each MPI rank)."""

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call _LogParserBase's post init
        if self.parse_only_rank is not None:
            if not (0 <= self.parse_only_rank < self.cfg.nprocs):
                raise ValueError(
                    f"parse_only_rank must be between 0 and nprocs-1, but got: {self.parse_only_rank}"
                )

    @property
    def ngen_log_dir(self):
        nld = os.environ.get(c.NGEN_LOG_DIR_KEY, None)
        if not nld:
            raise RuntimeError(f"Environment variable {c.NGEN_LOG_DIR_KEY} is not set.")
        return nld

    @property
    def ngen_log_dir_basename(self) -> str:
        return os.path.basename(self.ngen_log_dir)

    def ngen_log_basename(self, mpi_rank: int):
        """Basename of the ngen log file for the provided MPI rank."""
        if isinstance(self.cfg, RTEDefaultConfig):
            bn_prefix = self.rb.basin
        elif isinstance(self.cfg, RTECalibConfig):
            # NOTE determine where the 'calib' prefix is derived from and parameterize it instead of hardcoding it here.
            bn_prefix = "calib"
        elif isinstance(self.cfg, RTEForecastConfig):
            bn_prefix = self.rb.fcst_run_name
        elif isinstance(self.cfg, RTETestConfig):
            raise NotImplementedError(f"Unsupported config type: {type(self.cfg)}")
        else:
            raise NotImplementedError(f"Unsupported config type: {type(self.cfg)}")

        bn = f"{bn_prefix}_ngen_mpi_process_{mpi_rank}.log"
        return bn

    def ngen_log_path(self, mpi_rank: int) -> str:
        """Path of the ngen log file for the provided MPI rank."""
        return os.path.join(self.ngen_log_dir, self.ngen_log_basename(mpi_rank))


class _LogParserGeneric(_LogParserBase):
    """Parser for generic log files without MPI context, e.g. from nwm-fcst-mgr."""

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    log_file_path: Path | str
    """Only used by child class _LogParserGeneric, where one component may have a single log file. Explicit file path."""

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call _LogParserBase's post init
