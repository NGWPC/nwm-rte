from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import functools
import json
import os
import subprocess
import time
import traceback
from typing import Any, Dict

from pydantic import BaseModel, Field, ConfigDict, validate_call
from pydantic.json import pydantic_encoder

from mswm.build_inputs import RealizationBuilder
from mswm.utils.input_configuration import (
    InputConfig,
    GeneralConfig,
    CalibConfig,
    ForcingConfig,
    DataFileConfig,
    ParallelConfig,
)
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

from nwm_fcst_mgr.forecast import ForecastExecutionManager, RunStatus
from nwm_fcst_mgr.exceptions import NgenIntentionallyStoppedError


print = functools.partial(print, flush=True)

DIR_FORCING_RAW_INPUT = "/ngen-app/data/raw_input"


### .config section [Forcing]
DEFAULT_FORECAST_RUN_NAME = "fcst_run1"

# DEFAULT_FORCING_PROVIDER = "csv"
# FORCING_DIR =

DEFAULT_FORCING_PROVIDER = "bmi"
FORCING_DIR = None  # None when provider is bmi

FORCING_TEMPLATE_DIR = "/ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/"
FORCING_ROOT_DIR = "/ngen-app/data"
DT_START_FORECAST = datetime(year=2025, month=9, day=15, hour=0, minute=0, second=0)
DT_START_COLDSTART = DT_START_FORECAST - timedelta(days=2)
DT_END_COLDSTART = DT_START_FORECAST


### .config section [General]
DEFAULT_GAGE_ID = "01123000"
DEFAULT_GAGE_VINTAGE = "2025_Mar_14_21_14_37"

MODELS = "noah-owp-modular,cfe-s"
# MODELS="noah-owp-modular,topmodel"
DEFAULT_MAIN_DIR = "/ngwpc/run_ngen"
FORMULATION_NAME = f"test_{DEFAULT_FORCING_PROVIDER}"


### .config section [Calibration]
CALIB_OBJECTIVE_FUNCTION = "kge"
CALIB_OPTIMIZATION_ALGO = "dds"
CALIB_PARAMETERS_DIR = "/ngwpc/run_ngen/data/calib_params_tab_delimited"
CALIB_ITER_START = 0
CALIB_ITER_COUNT = 2
CALIB_SAVE_PLOT_ITER_FREQ = 1
DT_START_CALIB = datetime(year=2015, month=10, day=1, hour=0, minute=0, second=0)
DT_END_CALIB = DT_START_CALIB + timedelta(hours=47)

### .config section [DataFile]
MODULE_PARAMETER_FILES_DIR = "/ngen-app/nwm-msw-mgr/src/mswm/module_parameter_files"
NGEN_DIR = "/ngen-app/ngen"
HYDROFABRIC_DIR = "/s3/ngwpc-hydrofabric"


### .config section [Parallel]
DEFAULT_NPROCS = 1


### Test settings
### See this for full list of forcing configuration types: mswm.utils.input_configuration.mswm_valid_configs
FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT = ["short_range", "standard_ana", "medium_range_blend"]
# FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT = ["short_range"]
FORECAST_FORCING_CONFIGURATION_TYPES__ALL = [
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
    "nwm",
    "aorc",
]


@dataclass
class TestPaths:
    # From calibration
    gage_id: str
    gage_vintage: str
    obj_func: str
    optim_algo: str

    @property
    def dir_base(self) -> str:
        return (
            f"{DEFAULT_MAIN_DIR}/{CALIB_OBJECTIVE_FUNCTION}_{CALIB_OPTIMIZATION_ALGO}/{FORMULATION_NAME}/{self.gage_id}"
        )

    @property
    def dir_input(self) -> str:
        return f"{self.dir_base}/Input"

    @property
    def dir_output(self) -> str:
        return f"{self.dir_base}/Output"

    @property
    def ngen_log_file(self) -> str:
        return f"{self.dir_base}/logs/ngen.log"

    @property
    def calib_config_file(self) -> str:
        return f"{self.dir_base}/cold_start_workflow/input_calibration_{DEFAULT_FORCING_PROVIDER}.config"
        # return f"{self.dir_base}/cold_start_workflow/input_calibration_{DEFAULT_FORCING_PROVIDER}_short.config"

    @property
    def fcst_config_file(self) -> str:
        return f"{self.dir_base}/cold_start_workflow/input_forecast.config"

    @property
    def valid_yaml(self) -> str:
        return f"{self.dir_output}/Validation_Run/{self.gage_id}_config_valid_best.yaml"


def make_parallel_config(nprocs: int) -> ParallelConfig:
    if nprocs and nprocs > 1:
        parallel = ParallelConfig(
            parallel_ngen_exe="/ngen-app/ngen/cmake_build/ngen",
            partition_generator_exe="/ngen-app/ngen/cmake_build/partitionGenerator",
            nprocs=nprocs,
        )
    else:
        parallel = ParallelConfig(nprocs=nprocs)
    return parallel


def get_test_configs__calibration(
    nprocs: int = DEFAULT_NPROCS,
    gage_id: str = DEFAULT_GAGE_ID,
    gage_vintage: str = DEFAULT_GAGE_VINTAGE,
) -> list[InputConfig]:
    configs: list[InputConfig] = []

    forcing_config_types = CALIB_FORCING_CONFIGURATION_TYPES
    str_calib_start = DT_START_CALIB.strftime(DEFAULT_DATETIME_FORMAT)
    str_calib_end = DT_END_CALIB.strftime(DEFAULT_DATETIME_FORMAT)

    for fct in forcing_config_types:
        general = GeneralConfig(
            basin=gage_id,
            run_type="calibration",
            models=MODELS,
            formulation=FORMULATION_NAME,
            main_dir=DEFAULT_MAIN_DIR,
            start_period=str_calib_start,
            end_period=str_calib_end,
        )
        calibration = CalibConfig(
            optimization_algorithm=CALIB_OPTIMIZATION_ALGO,
            objective_function=CALIB_OBJECTIVE_FUNCTION,
            start_iteration=CALIB_ITER_START,
            number_iteration=CALIB_ITER_COUNT,
            calib_start_period=str_calib_start,
            calib_end_period=str_calib_end,
            calib_eval_start_period=str_calib_start,
            calib_eval_end_period=str_calib_end,
            valid_start_period=str_calib_start,
            valid_end_period=str_calib_end,
            valid_eval_start_period=str_calib_start,
            valid_eval_end_period=str_calib_end,
            full_eval_start_period=str_calib_start,
            full_eval_end_period=str_calib_end,
            save_plot_iter_freq=CALIB_SAVE_PLOT_ITER_FREQ,
            ngen_cerf=False,
            calib_parameter_file=CALIB_PARAMETERS_DIR,
        )
        forcing = ForcingConfig(
            forcing_provider=DEFAULT_FORCING_PROVIDER,
            forcing_dir=FORCING_DIR,
            forcing_template_dir=FORCING_TEMPLATE_DIR,
            root_dir=FORCING_ROOT_DIR,
            forcing_configuration=fct,
            cycle_datetime=DT_START_FORECAST.strftime(DEFAULT_DATETIME_FORMAT),
            cold_start_datetime=None,
        )
        datafile = DataFileConfig(
            hydrofab_file=f"{HYDROFABRIC_DIR}/2.2/CONUS/{gage_id}/GEOPACKAGE/USGS/{gage_vintage}/gauge_{gage_id}.gpkg",
            noah_parameter_dir=f"{MODULE_PARAMETER_FILES_DIR}/noah-owp-modular",
            ueb_parameter_dir=f"{MODULE_PARAMETER_FILES_DIR}/ueb",
            lasam_parameter_dir=f"{MODULE_PARAMETER_FILES_DIR}/lasam",
            lstm_parameter_dir=f"{MODULE_PARAMETER_FILES_DIR}/lstm",
            sac_parameter_dir=HYDROFABRIC_DIR,
            snow_17_parameter_dir=HYDROFABRIC_DIR,
            attributes_file="/ngwpc/run_ngen/data/conus_model_attributes.parquet",
            ngen_exe_file=f"{NGEN_DIR}/cmake_build/ngen",
            sloth_lib=f"{NGEN_DIR}/extern/sloth/cmake_build/libslothmodel.so",
            cfe_lib=f"{NGEN_DIR}/extern/cfe/cmake_build/libcfebmi.so",
            lasam_lib=f"{NGEN_DIR}/extern/LASAM/cmake_build/liblasambmi.so",
            noah_owp_modular_lib=f"{NGEN_DIR}/extern/noah-owp-modular/cmake_build/libsurfacebmi.so",
            pet_lib=f"{NGEN_DIR}/extern/evapotranspiration/evapotranspiration/cmake_build/libpetbmi.so",
            sac_sma_lib=f"{NGEN_DIR}/extern/sac-sma/cmake_build/libsacbmi.so",
            sft_lib=f"{NGEN_DIR}/extern/SoilFreezeThaw/cmake_build/libsftbmi.so",
            smp_lib=f"{NGEN_DIR}/extern/SoilMoistureProfiles/cmake_build/libsmpbmi.so",
            snow_17_lib=f"{NGEN_DIR}/extern/snow17/cmake_build/libsnow17bmi.so",
            topmodel_lib=f"{NGEN_DIR}/extern/topmodel/cmake_build/libtopmodelbmi.so",
            ueb_lib=f"{NGEN_DIR}/extern/ueb-bmi/cmake_build/src/libbmiuebcxx.so",
        )
        parallel = make_parallel_config(nprocs)
        configs.append(
            InputConfig(General=general, Calibration=calibration, Forcing=forcing, DataFile=datafile, Parallel=parallel)
        )

    return configs


def get_test_configs__forecast(
    do_all_forcing_configs: bool,
    use_cold_start: bool = False,
    # nprocs: int = DEFAULT_NPROCS,
) -> list[InputConfig]:
    configs: list[InputConfig] = []

    if use_cold_start:
        cold_start_datetime = DT_START_COLDSTART.strftime(DEFAULT_DATETIME_FORMAT)
        cycle_datetime = DT_END_COLDSTART.strftime(DEFAULT_DATETIME_FORMAT)
    else:
        cold_start_datetime = None
        cycle_datetime = DT_START_FORECAST.strftime(DEFAULT_DATETIME_FORMAT)

    if do_all_forcing_configs:
        forcing_config_types = FORECAST_FORCING_CONFIGURATION_TYPES__ALL
    else:
        forcing_config_types = FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT

    for fct in forcing_config_types:
        general = None
        forcing = ForcingConfig(
            forcing_provider=DEFAULT_FORCING_PROVIDER,
            forcing_dir=FORCING_DIR,
            forcing_template_dir=FORCING_TEMPLATE_DIR,
            root_dir=FORCING_ROOT_DIR,
            forcing_configuration=fct,
            cycle_datetime=cycle_datetime,
            cold_start_datetime=cold_start_datetime,
        )
        # parallel = make_parallel_config(nprocs)  # TODO adjust forecast manager to use this
        parallel = None
        configs.append(InputConfig(General=general, Forcing=forcing, Parallel=parallel))

    return configs


class TestStat(StrEnum):
    NOSTATUS = "NOSTATUS"
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


class LogParser(BaseModel):
    path: str
    # Don't include the entire file content when dumping this model
    content: str = Field(exclude=True, init=False, default=None)
    first_lines: list[str] = Field(init=False, default=None)
    last_lines: list[str] = Field(init=False, default=None)
    severe_lines: list[str] = Field(init=False, default=None)
    critical_lines: list[str] = Field(init=False, default=None)
    fatal_lines: list[str] = Field(init=False, default=None)

    def read_and_parse(self) -> None:
        severe = "SEVERE"
        critical = "CRITICAL"
        fatal = "FATAL"

        print(f"Reading: {self.path}")
        with open(self.path, "r") as f:
            self.content = f.read()

        lines = self.content.splitlines()
        self.first_lines = lines[:10]
        self.last_lines = lines[-10:]
        self.severe_lines = [l for l in lines if severe in l]
        self.critical_lines = [l for l in lines if critical in l]
        self.fatal_lines = [l for l in lines if fatal in l]


class ForecastTest(BaseModel):
    """
    Required attributes:
        rb_kwargs: dict

    # TODO also catch exceptions that happen during ForecastExecutionManager.preprocess
    # TODO is `ngen_log` different for standard_ana than for short_range?
    # TODO glean `ngen_log` from self.rb
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
    # Log created by ngen itself. Must be provided for forecast mode.  TODO glean this from rb.
    #   e.g. for forecast: ".../Output/Forecast_Run/fcst_run1/logs/ngen.log"
    #   TODO need to implement for calibration.
    ngen_log: LogParser = Field(init=False, default=None)
    # Log containing stdout+stderr stream of the subprocess call to ngen (ngen's terminal output).
    #   e.g. for forecast (from ForecastExecutionManager): ".../Output/Forecast_Run/fcst_run1/ngen_stdout_stderr.log"
    #   e.g. for calibration (from calibration.py): ".../Output/Calibration_Run/ngen_0pif3ish_worker/ngen_stdout_stderr.log"
    #   TODO need to implement for calibration. Read calib_log content to determine this path, since it shows the (randomized) name of the worker.
    exe_log: LogParser = Field(init=False, default=None)
    # Log created by calibration.py (can specify as CLI arg during call to calibration.py)
    calib_log: LogParser = Field(init=False, default=None)
    # Stderr lines of the subprocess call to calibration.py.
    calib_proc_stderr: list[str] = Field(init=False, default=[])

    def make_realization_builder__build_realization(self, build_method: str) -> None:
        """Instantiate the RealizationBuilder class and build the realization.
        build_method must be a valid build_method of RealizationBuilder, e.g. 'build_fcst_realization' or 'build_calibration_realization'.
        """
        try:
            self.rb = RealizationBuilder(**self.rb_kwargs)
            getattr(self.rb, build_method)()
        except Exception as e:
            print(
                f"Caught unexpected exception in main thread while instantiating RealizationBuilder or calling method {repr(build_method)}: {type(e)}: {repr(e)}. Storing exception info in test object to signify failure. Not reraising."
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

    def execute_calibration(self) -> None:
        if self.rb_stat != TestStat.PASS:
            raise RuntimeError(f"Cannot run calibration when realization did not build (self.rb_stat: {self.rb_stat})")

        current_time = datetime.now(timezone.utc).strftime(r"%Y%m%d_%H%M%S")
        calib_log_path_overwrite = os.path.join(self.rb.work_dir, "logs", f"calibration_{current_time}.log")
        self.calib_log = LogParser(path=calib_log_path_overwrite)

        print(f"Running calibration, will log to: {repr(self.calib_log.path)}")
        cmd = [
            "python",
            "/ngen-app/bin/calibration.py",
            str(self.rb.calib_config_file),
            "--log_path_overwrite",
            self.calib_log.path,
        ]
        print(f"Running command args: {cmd}")
        proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            proc.check_returncode()
        except Exception as e:
            print(
                f"Caught unexpected exception in main thread while executing calibration: {type(e)}: {repr(e)}. Storing exception info in test object to signify failure. Not reraising."
            )
            self.fcst_exe_stat = TestStat.FAIL
            self.fcst_exe_excep = e
            self.fcst_exe_excep_tb = traceback.format_exc().splitlines()
        else:
            self.fcst_exe_stat = TestStat.PASS
            self.fcst_exe_excep = None
            self.fcst_exe_excep_tb = []
        finally:
            self.calib_proc_stderr = proc.stderr.splitlines()
            if os.path.exists(self.calib_log.path):
                self.calib_log.read_and_parse()

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

        self.exe_log = LogParser(path=self.fcst_exe_mgr.log_handle.name)
        self.read_logs()

        if self.fcst_exe_excep is None:
            self.fcst_exe_excep_type = None
            self.fcst_exe_excep_msg = None
            if (not self.exe_log.fatal_lines) and (not self.ngen_log.fatal_lines):
                self.fcst_exe_stat = TestStat.PASS
            else:
                self.fcst_exe_stat = TestStat.FAIL
        else:
            self.fcst_exe_excep_type = str(type(self.fcst_exe_excep))
            self.fcst_exe_excep_msg = str(self.fcst_exe_excep)
            self.fcst_exe_stat = TestStat.FAIL

    def read_logs(self) -> None:
        self.exe_log.read_and_parse()
        self.ngen_log.read_and_parse()

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
        if os.path.exists(self.ngen_log.path):
            self.ngen_log.read_and_parse()
        else:
            print(f"Does not exist yet: {self.ngen_log.path}")
            return False
        # TODO improve this and confirm that it works for types other than short_range
        if (
            self.ngen_log.content.lower().count("processing forecast cycle") > 1
            and self.ngen_log.content.lower().count("writing output forcing file for timestamp") > 0
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

    def evaluate_test_results(self) -> None:
        test_results_file = os.path.join(os.path.dirname(__file__), "forecast_tests_results.json")
        msg = f"\n\n###### FORECAST TEST RESULTS ######\nWriting to: {test_results_file}\n{json.dumps(self.fcst_stat_sums, indent=2, default=pydantic_encoder)}"
        print(msg)
        with open(test_results_file, "w") as f:
            f.write(json.dumps(self.forecast_tests, indent=2, default=pydantic_encoder))
        if self.fcst_stat_sums.any_failed:
            raise RuntimeError(self.fcst_stat_sums)
