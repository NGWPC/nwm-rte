import functools
import os
import time
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from mswm.build_inputs import RealizationBuilder
from mswm.utils.input_configuration import InputConfig
from nwm_fcst_mgr.forecast import ForecastExecutionManager, RunStatus
from nwm_fcst_mgr.exceptions import NgenIntentionallyStoppedError


print = functools.partial(print, flush=True)


class ForecastExecutionTest(BaseModel):
    """
    Required attributes:
        rb: RealizationBuilder = Field(exclude=True)
        ngen_log_path: str

    # TODO also catch exceptions that happen during RealizationBuilder
    # TODO also catch exceptions that happen during ForecastExecutionManager.preprocess
    # TODO is `ngen_log_path` different for standard_ana than for short_range?
    # TODO glean `ngen_log_path` from self.rb
    """

    ##########
    ### Pydantic configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, strict=True)

    ##########
    ### Excluded attributes
    rb: RealizationBuilder = Field(exclude=True)
    fcst_exe_mgr: ForecastExecutionManager = Field(exclude=True, init=False, default=None)
    test_exception: Exception | None = Field(exclude=True, init=False, default=None)

    ##########
    ### Included attributes
    # Test result and errors
    test_passed: bool = Field(init=False, default=None)
    test_exception_type: str = Field(init=False, default=None)
    test_exception_msg: str = Field(init=False, default=None)
    # Forecast configuration
    coldstart: bool = Field(init=False, default=None)
    valid_yaml: str = Field(init=False, default=None)
    config: InputConfig = Field(init=False, default=None)
    # Log created by ngen itself
    ngen_log_path: str
    ngen_log_content: str = Field(init=False, default=None)
    # Log created by ForecastExecutionManager, e.g. ".../ngen_stdout_stderr.log"
    exe_output_log_path: str = Field(init=False, default=None)
    exe_output_log_content: str = Field(init=False, default=None)

    def model_post_init(self, __context: Any) -> None:
        self.coldstart = self.rb.use_cold_start
        self.valid_yaml = str(self.rb.valid_yaml)
        self.config = self.rb.input_configs_class

    def execute_forecast(
        self,
        quit_forecast_after_forcing_running: bool,
        quit_forecast_after_duration: bool,
    ) -> None:
        if quit_forecast_after_forcing_running:
            assert quit_forecast_after_duration is None
            async_waiter = functools.partial(self.wait_for_forcing_is_running)

        elif quit_forecast_after_duration is not None:
            assert not quit_forecast_after_forcing_running
            async_waiter = functools.partial(self.wait_for_duration, wait_duration_sec=quit_forecast_after_duration)

        else:
            async_waiter = None

        try:
            with ForecastExecutionManager(
                valid_yaml=self.rb.valid_yaml,
                real_path=str(self.rb.realization_file),
            ) as self.fcst_exe_mgr:
                self.fcst_exe_mgr.preprocess()
                if async_waiter:
                    self.fcst_exe_mgr.execute(wait=False)  # When wait=false, user polling is required
                    async_waiter()
                else:
                    self.fcst_exe_mgr.execute(wait=True)
        except NgenIntentionallyStoppedError as e:
            # Raised when stop flag is manually set, or when context manager ends before ngen finishes.
            # The latter is happening intentionally here.
            test_exception = None
        except Exception as e:
            print(f"Unexpected exception encountered when running forecast: {e}")
            test_exception = e
        else:
            test_exception = None
        self.test_exception = test_exception

        self.exe_output_log_path = self.fcst_exe_mgr.log_handle.name
        self.read_logs()
        self.test_exception_type = None if self.test_exception is None else str(type(self.test_exception))
        self.test_exception_msg = None if self.test_exception is None else str(self.test_exception)
        self.test_passed = True if self.test_exception is None else False

    def read_logs(self) -> None:
        print(f"Reading: {self.exe_output_log_path}")
        with open(self.exe_output_log_path, "r") as f:
            self.exe_output_log_content = f.read()

        print(f"Reading: {self.ngen_log_path}")
        with open(self.ngen_log_path, "r") as f:
            self.ngen_log_content = f.read()

    def wait_for_duration(self, wait_duration_sec: float):
        start = time.perf_counter()
        poll_freq_seconds = 2
        print(f"Polling ngen process every {poll_freq_seconds} seconds up to {wait_duration_sec} sec total duration...")
        while True:
            self.fcst_exe_mgr.poll_ngen_flush_log()
            duration_sec = time.perf_counter() - start
            if duration_sec > wait_duration_sec:
                print(f"After {duration_sec:.1f} seconds, quitting ngen intentionally")
                break
            if self.fcst_exe_mgr._status == RunStatus.EXECUTION_SUCCESS:
                print(f"After {duration_sec:.1f} seconds, ngen finished running")
                break
            time.sleep(poll_freq_seconds)

    def wait_for_forcing_is_running(self):
        start = time.perf_counter()
        poll_freq_seconds = 10
        print(f"Polling ngen process every {poll_freq_seconds} seconds...")
        while True:
            duration_sec = time.perf_counter() - start
            self.fcst_exe_mgr.poll_ngen_flush_log()
            if duration_sec > 10 and self.infer_from_log__forcing_is_running():
                print(f"After {duration_sec:.1f} seconds, ngen log indicates forcing is running successfully")
                break
            if self.fcst_exe_mgr._status == RunStatus.EXECUTION_SUCCESS:
                print(f"After {duration_sec:.1f} seconds, ngen finished running")
                break
            print(f"ngen has been running for {duration_sec:.1f} seconds...")
            # self.fcst_exe_mgr.schedule_ngen_stoppage()
            time.sleep(poll_freq_seconds)

    def infer_from_log__forcing_is_running(self) -> bool:
        """Read the log file and look for sentinel messages.
        If they exist, assume the forcing is running successfully and return True."""
        if os.path.exists(self.ngen_log_path):
            print(f"Reading: {self.ngen_log_path}")
            with open(self.ngen_log_path, "r") as f:
                log_content = f.read()
        else:
            print(f"Does not exist yet: {self.ngen_log_path}")
            return False
        if (
            log_content.lower().count("processing forecast cycle") > 1
            and log_content.lower().count("writing output forcing file for timestamp") > 0
        ):
            return True
        else:
            return False
