from datetime import datetime, timedelta
from enum import StrEnum
import functools
import os
import time
import traceback
from typing import Any, Dict

from pydantic import BaseModel, Field, ConfigDict, validate_call

from mswm.build_inputs import RealizationBuilder
from mswm.utils.input_configuration import InputConfig, GeneralConfig, ForcingConfig
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

from nwm_fcst_mgr.forecast import ForecastExecutionManager, RunStatus
from nwm_fcst_mgr.exceptions import NgenIntentionallyStoppedError


print = functools.partial(print, flush=True)


### .config section [Forcing]
FORECAST_RUN_NAME = "fcst_run1"
# FORCING_PROVIDER = "csv"
FORCING_PROVIDER = "bmi"
FORCING_DIR = None
FORCING_TEMPLATE_DIR = "/ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/"
FORCING_ROOT_DIR = "/ngen-app/data"
DT_START_FORECAST = datetime(year=2025, month=9, day=15, hour=0, minute=0, second=0)
DT_START_COLDSTART = DT_START_FORECAST - timedelta(days=2)
DT_END_COLDSTART = DT_START_FORECAST


### .config section [General]
GAGE_ID = "01123000"
MODELS = "noah-owp-modular,cfe-s"
# MODELS="noah-owp-modular,topmodel"
DEFAULT_MAIN_DIR = "/ngwpc/run_ngen"
FORMULATION_NAME = f"test_{FORCING_PROVIDER}"


### .config section [Calibration]
CALIB_OBJECTIVE_FUNCTION = "kge"
CALIB_OPTIMIZATION_ALGO = "dds"
DT_START_CALIB = datetime(year=2015, month=10, day=1, hour=0, minute=0, second=0)
DT_END_CALIB = DT_START_CALIB + timedelta(hours=47)


### Test settings
### See this for full list of forcing configuration types: mswm.utils.input_configuration.mswm_valid_configs
FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT = ["short_range", "standard_ana", "medium_range_blend"]
FORECAST_FORCING_CONFIGURATION_TYPES__ALL = [
    # "aorc",   # Calibration only
    # "nwm",    # Calibration only
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
CALIB_FORCING_CONFIGURATION_TYPES = [
    "aorc",
    "nwm",
]


def get_test_configs__forecast(do_all_forcing_configs: bool) -> list[InputConfig]:
    # TODO add coldstart option here
    configs: list[InputConfig] = []

    if do_all_forcing_configs:
        forcing_config_types = FORECAST_FORCING_CONFIGURATION_TYPES__ALL
    else:
        forcing_config_types = FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT

    for fct in forcing_config_types:
        general = None
        forcing = ForcingConfig(
            forcing_provider=FORCING_PROVIDER,
            forcing_dir=FORCING_DIR,
            forcing_template_dir=FORCING_TEMPLATE_DIR,
            root_dir=FORCING_ROOT_DIR,
            forcing_configuration=fct,
            cycle_datetime=DT_START_FORECAST.strftime(DEFAULT_DATETIME_FORMAT),
            cold_start_datetime=None,
        )

        configs.append(InputConfig(General=general, Forcing=forcing))

    return configs


class TestStat(StrEnum):
    NOSTATUS = "NOSTATUS"
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


class ForecastTest(BaseModel):
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
    fcst_exe_excep: Exception | None = Field(exclude=True, init=False, default=None)
    rb_excep: Exception | None = Field(exclude=True, init=False, default=None)

    ##########
    ### Included attributes
    # Test results and exceptions
    rb_stat: TestStat = Field(init=False, default=TestStat.NOSTATUS)
    rb_excep_type: str = Field(init=False, default=None)
    rb_excep_msg: str = Field(init=False, default=None)
    rb_excep_tb: list[str] = Field(init=False, default=[])  # Traceback lines
    fcst_exe_stat: TestStat = Field(init=False, default=TestStat.NOSTATUS)
    fcst_exe_excep_type: str = Field(init=False, default=None)
    fcst_exe_excep_msg: str = Field(init=False, default=None)
    fcst_exe_excep_tb: list[str] = Field(init=False, default=[])  # Traceback lines
    # Config kwargs
    rb_kwargs: dict
    # Log created by ngen itself
    ngen_log_path: str
    ngen_log_content: str = Field(init=False, default=None)
    ngen_log_severe_lines: list[str] = Field(init=False, default=[])
    ngen_log_critical_lines: list[str] = Field(init=False, default=[])
    ngen_log_fatal_lines: list[str] = Field(init=False, default=[])
    # Log created by ForecastExecutionManager, e.g. ".../ngen_stdout_stderr.log"
    exe_output_log_path: str = Field(init=False, default=None)
    exe_output_log_content: str = Field(init=False, default=None)
    exe_output_log_severe_lines: list[str] = Field(init=False, default=[])
    exe_output_log_critical_lines: list[str] = Field(init=False, default=[])
    exe_output_log_fatal_lines: list[str] = Field(init=False, default=[])

    def make_realization_builder__build_realization(self) -> None:
        """Instantiate the RealizationBuilder class and build the realization."""
        try:
            self.rb = RealizationBuilder(**self.rb_kwargs)
            self.rb.build_fcst_realization()
            # self.rb.build_default_realization()
        except Exception as e:
            print(
                f"Caught unexpected exception in main thread while building realization: {type(e)}: {repr(e)}. Storing exception info in test object to signify failure. Not reraising."
            )
            self.rb_excep = e
            self.rb_excep_tb = traceback.format_exc().splitlines()
        else:
            self.rb_excep = None
            self.rb_excep_tb = []

        if self.rb_excep is None:
            self.rb_stat = TestStat.PASS
            self.rb_excep_type = None
            self.rb_excep_msg = None
        else:
            self.rb_stat = TestStat.FAIL
            self.rb_excep_type = str(type(self.rb_excep))
            self.rb_excep_msg = str(self.rb_excep)
            # Also set forecast execution to fail, since it can't run if realization failed to build
            self.fcst_exe_stat = TestStat.FAIL

    def execute_forecast(
        self,
        quit_forecast_after_forcing_running: bool,
        quit_forecast_after_duration: bool,
    ) -> None:
        if self.rb_stat != TestStat.PASS:
            raise RuntimeError(f"Cannot run forecast when realization did not build (self.rb_stat: {self.rb_stat})")

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
                    # When wait=false, user polling is required
                    self.fcst_exe_mgr.execute(wait=False, log_file_open_mode="w")
                    async_waiter()
                else:
                    self.fcst_exe_mgr.execute(wait=True, log_file_open_mode="w")
        except KeyboardInterrupt as e:
            print(f"Caught KeyboardInterrupt in main thread. Reraising.")
            raise e
        except NgenIntentionallyStoppedError as e:
            # Raised when stop flag is manually set, or when context manager ends before ngen finishes.
            # The latter is happening intentionally here under certain types of tests.
            print(f"Caught NgenIntentionallyStoppedError in main thread. Not reraising.")
            fcst_exe_excep = None
        except Exception as e:
            print(
                f"Caught unexpected exception in main thread while executing forecast: {type(e)}: {repr(e)}. Storing exception info in test object to signify failure. Not reraising."
            )
            fcst_exe_excep = e
            self.fcst_exe_excep_tb = traceback.format_exc().splitlines()
        else:
            fcst_exe_excep = None
            self.fcst_exe_excep_tb = []

        self.fcst_exe_excep = fcst_exe_excep

        self.exe_output_log_path = self.fcst_exe_mgr.log_handle.name
        self.read_logs()

        if self.fcst_exe_excep is None:
            self.fcst_exe_excep_type = None
            self.fcst_exe_excep_msg = None
            if (not self.exe_output_log_fatal_lines) and (not self.ngen_log_fatal_lines):
                self.fcst_exe_stat = TestStat.PASS
            else:
                self.fcst_exe_stat = TestStat.FAIL
        else:
            self.fcst_exe_excep_type = str(type(self.fcst_exe_excep))
            self.fcst_exe_excep_msg = str(self.fcst_exe_excep)
            self.fcst_exe_stat = TestStat.FAIL

    def read_logs(self) -> None:
        severe = "SEVERE"
        critical = "CRITICAL"
        fatal = "FATAL"

        print(f"Reading: {self.exe_output_log_path}")
        with open(self.exe_output_log_path, "r") as f:
            self.exe_output_log_content = f.read()

        self.exe_output_log_severe_lines.extend([l for l in self.exe_output_log_content.splitlines() if severe in l])
        print(f"{len(self.exe_output_log_severe_lines)} {severe} lines in: {self.exe_output_log_path}")

        self.exe_output_log_critical_lines.extend(
            [l for l in self.exe_output_log_content.splitlines() if critical in l]
        )
        print(f"{len(self.exe_output_log_critical_lines)} {critical} lines in: {self.exe_output_log_path}")

        self.exe_output_log_fatal_lines.extend([l for l in self.exe_output_log_content.splitlines() if fatal in l])
        print(f"{len(self.exe_output_log_fatal_lines)} {fatal} lines in: {self.exe_output_log_path}")

        print(f"Reading: {self.ngen_log_path}")
        with open(self.ngen_log_path, "r") as f:
            self.ngen_log_content = f.read()

        self.ngen_log_severe_lines.extend([l for l in self.ngen_log_content.splitlines() if severe in l])
        print(f"{len(self.ngen_log_severe_lines)} {severe} lines in: {self.ngen_log_path}")

        self.ngen_log_critical_lines.extend([l for l in self.ngen_log_content.splitlines() if critical in l])
        print(f"{len(self.ngen_log_critical_lines)} {critical} lines in: {self.ngen_log_path}")

        self.ngen_log_fatal_lines.extend([l for l in self.ngen_log_content.splitlines() if fatal in l])
        print(f"{len(self.ngen_log_fatal_lines)} {fatal} lines in: {self.ngen_log_path}")

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
        # TODO improve this and confirm that it works for types other than short_range
        if (
            log_content.lower().count("processing forecast cycle") > 1
            and log_content.lower().count("writing output forcing file for timestamp") > 0
        ):
            return True
        else:
            return False


class TestResultsSums(BaseModel):
    rb_statcount: dict[str, int]  # Status counts for RealizationBuilder events
    fcst_exe_statcount: dict[str, int]  # Status counts for forecast execution events
    any_failed: bool = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        self.any_failed = (
            True if (self.rb_statcount[TestStat.FAIL] or self.fcst_exe_statcount[TestStat.FAIL]) else False
        )


class TestsManager(BaseModel):
    forecast_tests: list[ForecastTest] = Field(init=False, default=[])

    @validate_call
    def add_forecast_test(self, t: ForecastTest) -> None:
        self.forecast_tests.append(t)

    @property
    def fcst_stat_sums(self) -> TestResultsSums:
        # Initialize these to 0 count for each status option, then increment based on result from tests.
        rb_statcount = {status: 0 for status in TestStat}
        fcst_exe_statcount = {status: 0 for status in TestStat}
        for t in self.forecast_tests:
            rb_statcount[t.rb_stat] += 1
            fcst_exe_statcount[t.fcst_exe_stat] += 1

        return TestResultsSums(
            rb_statcount=rb_statcount,
            fcst_exe_statcount=fcst_exe_statcount,
        )
