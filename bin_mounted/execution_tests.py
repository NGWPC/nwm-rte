from datetime import datetime, timedelta
import functools
import os
import time
from typing import Any, Dict

from pydantic import BaseModel, Field, ConfigDict

from mswm.build_inputs import RealizationBuilder
from mswm.utils.input_configuration import InputConfig, GeneralConfig, ForcingConfig
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

from nwm_fcst_mgr.forecast import ForecastExecutionManager, RunStatus
from nwm_fcst_mgr.exceptions import NgenIntentionallyStoppedError


print = functools.partial(print, flush=True)


FORMULATION = "bmi"

FORECAST_START = datetime(year=2025, month=9, day=15, hour=0, minute=0, second=0)
COLDSTART_END = FORECAST_START
COLDSTART_START = COLDSTART_END - timedelta(days=2)


FORCING_CONFIGURATION_TYPES__DEFAULT = ["short_range", "standard_ana", "medium_range_blend"]

FORCING_CONFIGURATION_TYPES__ALL = [
    "aorc",
    "nwm",
    "standard_ana",
    "standard_ana_alaska",
    "standard_ana_hawaii",
    "standard_ana_puertorico",
    "extended_ana",
    "extended_ana_alaska",
    "short_range",
    "short_range_alaska",
    "short_range_hawaii",
    "short_range_puertorico",
    "short_range_extended_alaska",
    "medium_range_blend",
    "medium_range_blend_alaska",
    "long_range_mem1",
    "long_range_mem2",
    "long_range_mem3",
    "long_range_mem4",
]


def get_test_configs__forecast(do_all_forcing_configs: bool) -> list[InputConfig]:
    if do_all_forcing_configs:
        forcing_config_types = FORCING_CONFIGURATION_TYPES__ALL
    else:
        forcing_config_types = FORCING_CONFIGURATION_TYPES__DEFAULT

    configs = [
        InputConfig(
            Forcing=ForcingConfig(
                forcing_provider=FORMULATION,
                forcing_dir=None,
                forcing_template_dir="/ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/",
                root_dir="/ngen-app/data",
                forcing_configuration=fct,
                cycle_datetime=FORECAST_START.strftime(DEFAULT_DATETIME_FORMAT),
                cold_start_datetime=None,
            )
        )
        for fct in forcing_config_types
    ]

    return configs


class ForecastTestManager(BaseModel):
    """
    Required attributes:
        rb_kwargs: dict
        ngen_log_path: str

    # TODO also catch exceptions that happen during ForecastExecutionManager.preprocess
    # TODO is `ngen_log_path` different for standard_ana than for short_range?
    # TODO glean `ngen_log_path` from self.rb
    """

    ##########
    ### Pydantic configuration
    model_config = ConfigDict(arbitrary_types_allowed=True, strict=True)

    ##########
    ### Excluded attributes
    rb: RealizationBuilder = Field(exclude=True, init=False, default=None)
    fcst_exe_mgr: ForecastExecutionManager = Field(exclude=True, init=False, default=None)
    test_forecast_execution_exception: Exception | None = Field(exclude=True, init=False, default=None)
    test_realization_builder_exception: Exception | None = Field(exclude=True, init=False, default=None)

    ##########
    ### Included attributes
    # Test results and exceptions
    test_realization_builder_passed: bool = Field(init=False, default=False)
    test_forecast_execution_passed: bool = Field(init=False, default=False)
    test_realization_builder_exception_type: str = Field(init=False, default=None)
    test_realization_builder_exception_msg: str = Field(init=False, default=None)
    test_forecast_execution_exception_type: str = Field(init=False, default=None)
    test_forecast_execution_exception_msg: str = Field(init=False, default=None)
    # Config kwargs
    rb_kwargs: dict
    # Log created by ngen itself
    ngen_log_path: str
    ngen_log_content: str = Field(init=False, default=None)
    # Log created by ForecastExecutionManager, e.g. ".../ngen_stdout_stderr.log"
    exe_output_log_path: str = Field(init=False, default=None)
    exe_output_log_content: str = Field(init=False, default=None)

    def make_realization_builder__build_realization(self) -> None:
        """Instantiate the RealizationBuilder class and build the realization."""
        try:
            self.rb = RealizationBuilder(**self.rb_kwargs)
            self.rb.build_fcst_realization()
        except Exception as e:
            print(
                f"Caught unexpected exception in main thread while building realization: {type(e)}: {repr(e)}. Storing exception info in test object to signify failure. Not reraising."
            )
            self.test_realization_builder_exception = e
        else:
            self.test_realization_builder_exception = None

        if self.test_realization_builder_exception is None:
            self.test_realization_builder_passed = True
            self.test_realization_builder_exception_type = None
            self.test_realization_builder_exception_msg = None
        else:
            self.test_realization_builder_passed = False
            self.test_realization_builder_exception_type = str(type(self.test_realization_builder_exception))
            self.test_realization_builder_exception_msg = str(self.test_realization_builder_exception)

    def execute_forecast(
        self,
        quit_forecast_after_forcing_running: bool,
        quit_forecast_after_duration: bool,
    ) -> None:
        if not self.test_realization_builder_passed:
            raise RuntimeError(
                f"Cannot run forecast when realization did not build (self.test_realization_builder_passed == {self.test_realization_builder_passed})"
            )

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
        except KeyboardInterrupt as e:
            print(f"Caught KeyboardInterrupt in main thread. Reraising.")
            raise e
        except NgenIntentionallyStoppedError as e:
            # Raised when stop flag is manually set, or when context manager ends before ngen finishes.
            # The latter is happening intentionally here under certain types of tests.
            print(f"Caught NgenIntentionallyStoppedError in main thread. Not reraising.")
            test_forecast_execution_exception = None
        except Exception as e:
            print(
                f"Caught unexpected exception in main thread while executing forecast: {type(e)}: {repr(e)}. Storing exception info in test object to signify failure. Not reraising."
            )
            test_forecast_execution_exception = e
        else:
            test_forecast_execution_exception = None
        self.test_forecast_execution_exception = test_forecast_execution_exception

        self.exe_output_log_path = self.fcst_exe_mgr.log_handle.name
        self.read_logs()

        if self.test_forecast_execution_exception is None:
            self.test_forecast_execution_passed = True
            self.test_forecast_execution_exception_type = None
            self.test_forecast_execution_exception_msg = None
        else:
            self.test_forecast_execution_passed = False
            self.test_forecast_execution_exception_type = str(type(self.test_forecast_execution_exception))
            self.test_forecast_execution_exception_msg = str(self.test_forecast_execution_exception)

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
