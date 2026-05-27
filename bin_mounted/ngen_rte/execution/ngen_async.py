"""Async ngen execution, live status polling, live log parsing.
Reads logs for:
    1. ngen per-MPI-rank
    2. ngen stdout+stderr
    3. nwm-fcst-mgr
    4. nwm-msw-mgr
"""

import os
import time
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path

from ewts import LogParts
from mswm.build_inputs import RealizationBuilder
from ngen_rte.execution.ngen_logs import (
    _LogParserBase,
    _LogParserGeneric,
    _LogParserNgen,
)
from ngen_rte.utils import transmit
from nwm_fcst_mgr.exceptions import (
    NgenCalledProcessError,
    NgenIntentionallyStoppedError,
)
from nwm_fcst_mgr.forecast import ConfigCache, ForecastExecutionManager, RunStatus
from pydantic import BaseModel, ConfigDict, Field

PARSE_ONLY_RANK = None
"""Set this to an integer to restrict the log parser / payload transmitter to only that MPI rank.
If None, all MPI ranks will be parsed and transmitted."""

NGEN_EXECUTION_POLL_CONTINUE_STATUSES = {
    RunStatus.NOSTATUS,
    RunStatus.PREPROCESSED,
    RunStatus.EXECUTION_RUNNING,
}
"""The status enum values that cause the async parsing / polling to continue.
When the status is no longer in this set, this indicates that ngen has stopped
(finished, crashed, timed out, or intentionally stopped)."""

FINAL_WAIT = 2
"""After status indicates that the ngen run has stopped, wait this many seconds before reading the logs one last time."""


class NgenRunnerAsync(BaseModel):
    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    rb: RealizationBuilder
    parse_only_rank: int | None = PARSE_ONLY_RANK
    postprocess: bool = False
    """If True, call ForecastExecutionManager.postprocess() after ngen finishes, before the final log reads."""
    suppress_output: bool = False
    """Passed to ForecastExecutionManager.postprocess()"""
    timeout_secs: float | None = None

    fem: ForecastExecutionManager | None = Field(default=None, init=False)
    log_parsers: list[_LogParserBase] = Field(default_factory=list, init=False)
    """The ngen parser is assumed to be the first in the list"""

    def model_post_init(self, __context) -> None:
        self._register_initial_log_parser()
        self._deadline = (
            time.perf_counter() + self.timeout_secs
            if self.timeout_secs is not None
            else float("inf")
        )

    def _register_initial_log_parser(self):
        """Register log log_parsers that are always included.
        The ngen log parser has specific behavior (e.g. for multiple MPI ranks)
        and is assumed to be first in the list"""
        # ngen MPI ranks
        self._register_log_parser(
            _LogParserNgen(rb=self.rb, parse_only_rank=self.parse_only_rank)
        )
        # mswm
        self._register_log_parser(
            _LogParserGeneric(log_file_path=self.rb.log_file_path)
        )

    def __del__(self):
        self.close()

    def close(self):
        """Called by destructor. Call the ForecastExecutionManager's close() method and destroy it."""
        if self.fem is not None:
            self.fem.close()
            self.fem = None

    def _register_log_parser(self, parser: _LogParserBase) -> None:
        """Append to the list of log log_parsers to read from."""
        self.log_parsers.append(parser)

    def start(self) -> None:
        """Start the ngen forecast run asynchronously."""
        if self.fem is not None:
            raise RuntimeError("Execution mgr has already been set")

        print("Starting ngen run...")
        config_cache = self._make_config_cache()
        if self.rb.run_type in ("forecast", "default"):
            self.fem = ForecastExecutionManager(
                real_path=str(self.rb.realization_file),
                config_cache=config_cache,
                partition_file=self.rb.part_file,
            )
            # Watch log files for the nwm_fcst_mgr package and the ngen subprocess stdout+stderr.
            self._register_log_parser(
                _LogParserGeneric(log_file_path=self.fem.fcst_mgr_log_file_path)
            )
            self._register_log_parser(
                _LogParserGeneric(
                    log_file_path=self.fem.ngen_proc_stdout_stderr_log_file_path,
                    tolerant=True,
                )
            )
            self.fem.preprocess()
            self.fem.execute(wait=False, log_file_open_mode="w")
        elif self.rb.run_type == "calibration":
            raise NotImplementedError(
                f"Unsupported realization type: {self.rb.run_type}"
            )
        else:
            raise ValueError(f"Unsupported realization type: {self.rb.run_type}")

    def stream_status_until_complete(self) -> None:
        """Stream status updates from the running forecast until completion."""
        try:
            for (
                mpi_rank,
                new_log_parts,
                log_file,
            ) in self._iter_new_log_parts_until_complete():
                transmit(mpi_rank, new_log_parts, log_file)
        except NgenCalledProcessError as e:
            raise RuntimeError(f"Error during forecast run: {e}") from e
        except NgenIntentionallyStoppedError as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Unexpected exception during ngen run: {e}") from e
        finally:
            if self.fem is not None:
                self.fem.close()
                self.fem = None
        errors: list[Exception] = []
        for mpi_rank in range(self.rb.input_configs["Parallel"]["nprocs"]):
            # NOTE: this assumes that the first parser in the list is for the ngen MPI ranks.
            if (
                mpi_rank not in self.log_parsers[0].log_lines_hash_cache
                or len(self.log_parsers[0].log_lines_hash_cache[mpi_rank]) == 0
            ):
                errors.append(
                    RuntimeError(
                        f"No log lines were parsed for MPI rank ngen logs for rank {mpi_rank}."
                    )
                )
        if errors:
            raise RuntimeError(errors)

    def _make_config_cache(self) -> ConfigCache | None:
        """Make and return a ConfigCache based on the type of realization."""
        if self.rb.run_type == "forecast":
            config_cache = ConfigCache(valid_yaml=self.rb.valid_yaml, no_valid=False)
        elif self.rb.run_type == "default":
            config_cache = ConfigCache(
                run_dir=os.path.dirname(self.rb.realization_file), no_valid=True
            )
        elif self.rb.run_type == "calibration":
            raise NotImplementedError(
                f"Unsupported realization type: {self.rb.run_type}"
            )
        else:
            raise ValueError(f"Unsupported realization type: {self.rb.run_type}")
        return config_cache

    def _iter_new_log_parts(
        self, final: bool = False
    ) -> Generator[tuple[int, LogParts, Path | str], None, None]:
        """Generator that yields (mpi_rank, log_parts, log_file) tuples for each new message.
        If this is the final call, wait FINAL_WAIT seconds before reading logs, and optionally call postprocess() before that."""
        if final:
            if self.postprocess:
                if self.fem._status != RunStatus.EXECUTION_SUCCESS:
                    print(
                        f"Would have called execution mgr postprocess(), but cannot since status = {self.fem._status}"
                    )
                else:
                    print("Calling execution mgr postprocess()")
                    self.fem.postprocess(suppress_output=self.suppress_output)
            print(f"Waiting {FINAL_WAIT} seconds before final read of logs...")
            time.sleep(FINAL_WAIT)
        print(
            f"Execution mgr: {self.fem._status} at {datetime.now(timezone.utc).isoformat()}"
        )
        for parser in self.log_parsers:
            for mpi_rank, new_log_parts, log_file in parser._new_log_parts():
                yield mpi_rank, new_log_parts, log_file

    def _iter_new_log_parts_until_complete(
        self,
    ) -> Generator[tuple[int, LogParts, Path | str], None, None]:
        """Generator that yields (mpi_rank, log_parts, log_file) tuples for each new message, until ngen finishes."""
        if self.fem is None:
            raise RuntimeError("Execution mgr is not set. Call start() first.")

        first = True
        try:
            while first or self.fem._status in NGEN_EXECUTION_POLL_CONTINUE_STATUSES:
                first = False
                self.fem.poll_ngen_flush_log()
                yield from self._iter_new_log_parts()
                if time.perf_counter() >= self._deadline:
                    self.fem.schedule_ngen_stoppage()
        except Exception as e:
            raise e
        finally:
            yield from self._iter_new_log_parts(final=True)
