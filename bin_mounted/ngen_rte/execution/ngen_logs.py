"""Live polling of ngen log files"""

import os
import time
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path

import ngen_rte.consts as c
from ewts import LogParts, parts_of_log_line
from mswm.build_inputs import RealizationBuilder
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT as DDF
from ngen_rte.logger import initialize_logger
from pydantic import BaseModel, ConfigDict, Field

LOG = initialize_logger()


THROTTLE_SECONDS = 3


class TestLines(BaseModel):
    """For usage by execution_tests.py"""

    first_lines: list[str]
    last_lines: list[str]
    severe_lines: list[str]
    critical_lines: list[str]
    fatal_lines: list[str]


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

    log2testlines: dict[Path | str, TestLines] = Field(default_factory=dict, init=False)
    """Used by execution_tests.py"""

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
            for mpi_rank in range(self.rb.input_configs["Parallel"]["nprocs"]):
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
                LOG.debug(f"log file does not yet exist: {log_file_path}")
                continue
            LOG.debug(f"Reading: {log_file_path}")
            with open(log_file_path) as f:
                for line in f:
                    if not self._line_is_new(mpi_rank, line):
                        continue
                    line = line.rstrip()
                    try:
                        parts = parts_of_log_line(line, tolerant=self.tolerant)
                    except Exception as e:
                        LOG.error(
                            f"Error parsing line into parts: {line}. Error: {e}. Traceback: {traceback.format_exc()}"
                        )
                        continue
                    result.append((mpi_rank, parts, log_file_path))
        return result

    def read_and_parse_all_lines_for_issues(self) -> None:
        """Code migrated from earlier execution_tests.py script. For roughly detecting reportable log levels
        when running execution tests in series, and tracking the first and last lines of each log file.
        TODO also inspect payloads if they exist."""
        severe = "SEVERE"
        critical = "CRITICAL"
        fatal = "FATAL"

        self.log2testlines: dict[Path | str, TestLines] = {}

        for mpi_rank, log_file_path in self._iter_log_paths():
            LOG.info(f"Reading in full to build TestLines: {log_file_path}")
            with open(log_file_path, "r") as f:
                all_lines = f.read().splitlines()
            test_lines = TestLines(
                first_lines=all_lines[:10],
                last_lines=all_lines[-10:],
                severe_lines=[ln for ln in all_lines if severe in ln],
                critical_lines=[ln for ln in all_lines if critical in ln],
                fatal_lines=[ln for ln in all_lines if fatal in ln],
            )
            LOG.info(
                f"{log_file_path} has {len(all_lines)} total lines including {len(test_lines.severe_lines)} severe, {len(test_lines.critical_lines)} critical, {len(test_lines.fatal_lines)} fatal"
            )
            self.log2testlines[log_file_path] = test_lines


class _LogParserNgen(_LogParserBase):
    """Parser for ngen log files with MPI awareness."""

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    rb: RealizationBuilder
    parse_only_rank: int | None
    """Only used by child class _LogParserNgen, where one component may have multiple logs (one for each MPI rank)."""

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call _LogParserBase's post init
        if self.parse_only_rank is not None:
            if not (
                0 <= self.parse_only_rank < self.rb.input_configs["Parallel"]["nprocs"]
            ):
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
        if self.rb.run_type == "default":
            bn_prefix = self.rb.basin
        elif self.rb.run_type == "calibration":
            # NOTE determine where the 'calib' prefix is derived from and parameterize it instead of hardcoding it here.
            bn_prefix = "calib"
        elif self.rb.run_type == "forecast":
            bn_prefix = self.rb.fcst_run_name
        else:
            raise NotImplementedError(
                f"Unsupported realization type: {self.rb.run_type}"
            )

        bn = f"{bn_prefix}_ngen_mpi_process_{mpi_rank}.log"
        return bn

    def ngen_log_path(self, mpi_rank: int) -> str:
        """Path of the ngen log file for the provided MPI rank."""
        return os.path.join(self.ngen_log_dir, self.ngen_log_basename(mpi_rank))


class _LogParserGeneric(_LogParserBase):
    """Parser for generic log files without MPI context, e.g. from nwm-fcst-mgr."""

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    log_file_path: Path | str

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call _LogParserBase's post init


def dict_factory(fields) -> dict:
    """For dataclass ensuring a certain order of Payload keys, and reporting str versions of enums,
    when serializing to log messages, for human readability."""
    first_key = "modnm"
    ordered = []
    rest = []
    for k, v in fields:
        # Convert enum values to string
        if isinstance(v, Enum):
            v = str(v)
        # Convert datetime values to string
        if isinstance(v, datetime):
            v = v.strftime(DDF)
        if k == first_key:
            ordered.append((k, v))
        else:
            rest.append((k, v))
    return dict(ordered + rest)
