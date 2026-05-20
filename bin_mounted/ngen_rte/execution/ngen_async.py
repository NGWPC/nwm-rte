"""Async ngen execution, live status polling, live log parsing.
Reads ngen's per-MPI-rank logs.
TODO: Read the ngen proc's stdout+stderr streams (or associated log file).
TODO: Read msw-mgr's log.
TODO: Read fcst-mgr's log.
TODO: Make log discovery (in ngen_logs.py) more robust, and add support for behavior of optional NGEN_LOG_TO_RTE env var.
"""

import os
import time
from collections.abc import Generator
from dataclasses import asdict
from datetime import datetime, timezone

from ewts import LogParts
from mswm.build_inputs import RealizationBuilder
from ngen_rte.configs import (
    RTEBaseConfig,
    RTECalibConfig,
    RTEDefaultConfig,
    RTEForecastConfig,
)
from ngen_rte.execution.ngen_logs import _NgenLogsParser
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

    cfg: RTEBaseConfig
    rb: RealizationBuilder
    parse_only_rank: int | None = PARSE_ONLY_RANK
    postprocess: bool = False
    """If True, call ForecastExecutionManager.postprocess() after ngen finishes, before the final log reads."""
    suppress_output: bool = False
    """Passed to ForecastExecutionManager.postprocess()"""

    fem: ForecastExecutionManager | None = Field(default=None, init=False)
    logs_parser: _NgenLogsParser | None = Field(default=None, init=False)

    def model_post_init(self, __context) -> None:
        self.logs_parser = _NgenLogsParser(
            cfg=self.cfg,
            rb=self.rb,
            parse_only_rank=self.parse_only_rank,
        )

    def __del__(self):
        self.close()

    def close(self):
        """Called by destructor. Call the ForecastExecutionManager's close() method and destroy it."""
        if self.fem is not None:
            self.fem.close()
            self.fem = None

    def start(self) -> None:
        """Start the ngen forecast run asynchronously."""
        if self.fem is not None:
            raise RuntimeError("Execution mgr has already been set")

        print("Starting ngen run...")
        config_cache = self._make_config_cache()
        if isinstance(self.cfg, (RTEForecastConfig, RTEDefaultConfig)):
            self.fem = ForecastExecutionManager(
                real_path=str(self.rb.realization_file),
                config_cache=config_cache,
                partition_file=self.rb.part_file,
            )
            self.fem.preprocess()
            self.fem.execute(wait=False, log_file_open_mode="w")
        elif isinstance(self.cfg, RTECalibConfig):
            raise NotImplementedError(f"Unsupported config type: {type(self.cfg)}")
        else:
            raise ValueError(f"Unsupported config type: {type(self.cfg)}")

    def stream_status_until_complete(self) -> None:
        """Stream status updates from the running forecast until completion."""
        try:
            for mpi_rank, new_log_parts in self._iter_new_log_parts_until_complete():
                self._transmit(mpi_rank, new_log_parts)
        except NgenCalledProcessError as e:
            raise RuntimeError(f"Error during forecast run: {e}") from e
        except NgenIntentionallyStoppedError as e:
            raise RuntimeError(f"ngen intentionally stopped: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Error during ngen run: {e}") from e
        finally:
            if self.fem is not None:
                self.fem.close()

    def _make_config_cache(self) -> ConfigCache | None:
        """Make and return a ConfigCache based on the type of cfg."""
        if isinstance(self.cfg, RTEForecastConfig):
            config_cache = ConfigCache(valid_yaml=self.rb.valid_yaml, no_valid=False)
        elif isinstance(self.cfg, RTEDefaultConfig):
            config_cache = ConfigCache(
                run_dir=os.path.dirname(self.rb.realization_file), no_valid=True
            )
        elif isinstance(self.cfg, RTECalibConfig):
            raise NotImplementedError(f"Unsupported config type: {type(self.cfg)}")
        else:
            raise ValueError(f"Unsupported config type: {type(self.cfg)}")
        return config_cache

    def _iter_new_log_parts(
        self, final: bool = False
    ) -> Generator[tuple[int, LogParts], None, None]:
        """Generator that yields (mpi_rank, log_parts) tuples for each new message."""
        if final:
            if self.postprocess:
                print("Calling execution mgr postprocess()")
                self.fem.postprocess(suppress_output=self.suppress_output)
            print(f"Waiting {FINAL_WAIT} seconds before final read of ngen logs...")
            time.sleep(FINAL_WAIT)
        print(
            f"Execution mgr: {self.fem._status} at {datetime.now(timezone.utc).isoformat()}"
        )
        for mpi_rank, new_log_parts in self.logs_parser._new_log_parts():
            yield mpi_rank, new_log_parts

    def _iter_new_log_parts_until_complete(
        self,
    ) -> Generator[tuple[int, LogParts], None, None]:
        """Generator that yields (mpi_rank, log_parts) tuples for each new message, until ngen finishes."""
        if self.fem is None:
            raise RuntimeError("Execution mgr is not set. Call start() first.")

        first = True
        try:
            while first or self.fem._status in NGEN_EXECUTION_POLL_CONTINUE_STATUSES:
                first = False
                self.fem.poll_ngen_flush_log()
                yield from self._iter_new_log_parts()
        except Exception as e:
            raise RuntimeError(f"Error while polling for forecast status: {e}") from e
        finally:
            yield from self._iter_new_log_parts(final=True)

    def _transmit(self, mpi_rank: int, log_parts: LogParts) -> None:
        """Transmit information about the run."""
        # TODO implement actual transmission logic (send to file or service)
        # TODO get these log levels from an enum (from ewts?)
        if log_parts.level in ("WARNING", "ERROR", "CRITICAL", "SEVERE", "FATAL"):
            print(f"Concern: rank {mpi_rank}: {log_parts}")
        if log_parts.payload:
            print(
                f"Transmitting payload from rank {mpi_rank}: {asdict(log_parts.payload)}"
            )
