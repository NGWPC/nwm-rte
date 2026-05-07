# ruff: noqa: E741

import functools
import itertools
import json
import os
import subprocess
import time
import traceback
from datetime import datetime, timezone
from enum import StrEnum

import consts as c
from configs import (
    CalibTimeWindows,
    ForcingProviderPaths,
    ModelFormulation,
    build_model_formulations_for_test,
    get_data_paths_for_lstm,
    make_parallel_config,
)
from mswm.build_inputs import RealizationBuilder
from mswm.utils.input_configuration import (
    CalibConfig,
    DataFileConfig,
    ForcingConfig,
    GeneralConfig,
    InputConfig,
    ModulePropertiesConfig,
)
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT as DDF
from nwm_fcst_mgr.exceptions import NgenIntentionallyStoppedError
from nwm_fcst_mgr.forecast import ConfigCache, ForecastExecutionManager, RunStatus
from pydantic import BaseModel, ConfigDict, Field, validate_call
from pydantic.json import pydantic_encoder

print = functools.partial(print, flush=True)


def get_test_configs__calibration(
    nprocs: int = c.DEFAULT_NPROCS,
    gage_id: str = c.DEFAULT_GAGE_ID,
    hydrofab_file: str | None = None,
    obj_func: c.CalObjective = c.CALIB_OBJECTIVE_FUNCTION,
    optim_algo: c.CalOptimizationAlgo = c.CALIB_OPTIMIZATION_ALGO,
    model_formulation: ModelFormulation | None = None,
    # For iterating over multiple model formulations
    model_formulations_file: str | None = None,
    forcing_config_types=c.CALIB_FORCING_TYPES,
    global_domain: str = c.GLOBAL_DOMAINS[0],
    forcing_static_dir: str = c.FORCING_STATIC_DIR_DEFAULT,
    windows: CalibTimeWindows = CalibTimeWindows(),
    run_type: str = "calibration",
) -> list[InputConfig]:
    """Build and return a list of InputConfig instances to be used for building calibration realizations.
    If the model_formulations_file is provided, it will be parsed to determine which formulations to run.
    Otherwise, the default formulation from consts.DEFAULT_MODEL_FORMULATION_ARGS will be ran."""
    if run_type not in ("calibration", "default"):
        raise ValueError(f"Unexpected run_type: {run_type}")

    if model_formulations_file:
        model_formulations = build_model_formulations_for_test(model_formulations_file)
    elif model_formulation is not None:
        model_formulations = [model_formulation]
    else:
        model_formulations = [ModelFormulation(*c.DEFAULT_MODEL_FORMULATION_ARGS)]

    fpp = ForcingProviderPaths(
        global_domain=global_domain,
        forcing_static_dir=forcing_static_dir,
    )

    configs: list[InputConfig] = []

    calibration = CalibConfig(
        optimization_algorithm=optim_algo,
        swarm_size=c.CALIB_SWARM_SIZE,
        c1=c.CALIB_PSO_C1,
        c2=c.CALIB_PSO_C2,
        w=c.CALIB_PSO_W,
        objective_function=obj_func,
        start_iteration=c.CALIB_ITER_START,
        number_iteration=c.CALIB_ITER_COUNT,
        calib_output_vars=True,
        valid_output_vars=True,
        calib_start_period=windows.calib_sim_start.strftime(DDF),
        calib_end_period=windows.calib_sim_end.strftime(DDF),
        calib_eval_start_period=windows.calib_eval_start.strftime(DDF),
        calib_eval_end_period=windows.calib_eval_end.strftime(DDF),
        valid_start_period=windows.valid_sim_start.strftime(DDF),
        valid_end_period=windows.valid_sim_end.strftime(DDF),
        valid_eval_start_period=windows.valid_eval_start.strftime(DDF),
        valid_eval_end_period=windows.valid_eval_end.strftime(DDF),
        full_eval_start_period=windows.full_eval_start.strftime(DDF),
        full_eval_end_period=windows.full_eval_end.strftime(DDF),
        save_plot_iter_freq=c.CALIB_SAVE_PLOT_ITER_FREQ,
        ngen_cerf=False,
        calib_parameter_file=c.CALIB_PARAMETERS_DIR,
    )

    parallel = make_parallel_config(nprocs)

    for mf, fct in itertools.product(model_formulations, forcing_config_types):
        general = GeneralConfig(
            basin=gage_id,
            run_type=run_type,
            models=mf.models_csv,
            formulation=fpp.formulation_name,
            main_dir=c.DEFAULT_MAIN_DIR,
            start_period=windows.calib_eval_start.strftime(DDF),
            end_period=windows.calib_eval_end.strftime(DDF),
            output_precip=True,
            output_swe=True,
            output_sm=True,
            domain=global_domain.lower(),
        )

        module_properties = ModulePropertiesConfig(cfe_aet_rootzone=mf.cfe_aet_rootzone)

        forcing = ForcingConfig(
            forcing_provider=c.FORCING_PROVIDER,
            forcing_dir=forcing_static_dir,
            forcing_template_dir=c.FORCING_TEMPLATE_DIR,
            root_dir=c.FORCING_ROOT_DIR,
            forcing_configuration=fct,
            cycle_datetime=windows.calib_sim_start.strftime(DDF),
            cold_start_datetime=None,
            global_domain=global_domain,
            forcing_static_dir=forcing_static_dir,
            scratch_dir_override=c.SCRATCH_DIR_OVERRIDE,
            forcing_product_versions=c.FORCING_PRODUCT_VERSIONS_DICT,
        )

        obs_dir, nwmretro_file, errors = get_data_paths_for_lstm(
            global_domain,
            gage_id,
            models_csv=mf.models_csv,
        )
        if errors:
            raise RuntimeError(errors)

        datafile = DataFileConfig(
            **(
                c.DATAFILE_LIBS
                | {
                    "obs_dir": obs_dir,
                    "nwmretro_file": nwmretro_file,
                    "hydrofab_file": hydrofab_file,
                }
            ),
        )

        configs.append(
            InputConfig(
                General=general,
                ModuleProperties=module_properties,
                Calibration=calibration,
                Forcing=forcing,
                DataFile=datafile,
                Parallel=parallel,
            )
        )

    return configs


def get_test_configs__forecast(
    do_all_forcing_configs: bool,
    use_cold_start: bool = False,
    nprocs: int = c.DEFAULT_NPROCS,
) -> list[InputConfig]:
    """Build and return a list of InputConfig instances to be used for building forecast realizations."""
    configs: list[InputConfig] = []

    if use_cold_start:
        cold_start_datetime = c.DT_START_COLDSTART.strftime(DDF)
        cycle_datetime = c.DT_END_COLDSTART.strftime(DDF)
    else:
        cold_start_datetime = None
        cycle_datetime = c.DT_START_FORECAST.strftime(DDF)

    if do_all_forcing_configs:
        forcing_config_types = c.FORECAST_FORCING_TYPES
    else:
        forcing_config_types = c.FORECAST_FORCING_TYPES__TESTS

    for fct in forcing_config_types:
        general = None
        forcing = ForcingConfig(
            forcing_provider=c.FORCING_PROVIDER,
            forcing_dir=self.forcing_static_dir,
            forcing_template_dir=c.FORCING_TEMPLATE_DIR,
            root_dir=c.FORCING_ROOT_DIR,
            forcing_configuration=fct,
            cycle_datetime=cycle_datetime,
            cold_start_datetime=cold_start_datetime,
            scratch_dir_override=c.SCRATCH_DIR_OVERRIDE,
            forcing_product_versions=c.FORCING_PRODUCT_VERSIONS_DICT,
        )
        parallel = make_parallel_config(nprocs)
        configs.append(InputConfig(General=general, Forcing=forcing, Parallel=parallel))

    return configs


class TestStat(StrEnum):
    """Status enumerator for test execution"""

    NOSTATUS = "NOSTATUS"
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


class LogParser(BaseModel):
    """Helper class that reads various ngen log files and reports certain messages from them"""

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
    For managed execution of a set of realizations, with error trapping.
    Covers forecasts and calibrations.
    Use with the TestsManager class.

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
    fcst_exe_mgr: ForecastExecutionManager = Field(
        exclude=True, init=False, default=None
    )
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
    ### TODO update ngen_log to work with new EWTS per-rank logs, and new RTE log paths
    # ngen_log: LogParser = Field(init=False, default=None)
    # Log containing stdout+stderr stream of the subprocess call to ngen (ngen's terminal output).
    #   e.g. for forecast (from ForecastExecutionManager): ".../Output/Forecast_Run/fcst_run1/ngen_stdout_stderr.log"
    #   e.g. for calibration (from calibration executable): ".../Output/Calibration_Run/ngen_0pif3ish_worker/ngen_stdout_stderr.log"
    #   TODO need to implement for calibration. Read calib_log content to determine this path, since it shows the (randomized) name of the worker.
    exe_log: LogParser = Field(init=False, default=None)
    # Log created by calibration executable (can specify as CLI arg during call to calibration executable)
    calib_log: LogParser = Field(init=False, default=None)
    # Stderr lines of the subprocess call to calibration executable.
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

    def execute_calibration(
        self,
        quit_calibration_after_duration: float | None,
        worker_name: str | None = None,
    ) -> None:
        """Run the calibration realization, optionally stopping ngen after `quit_calibration_after_duration` seconds."""
        if self.rb_stat != TestStat.PASS:
            raise RuntimeError(
                f"Cannot run calibration when realization did not build (self.rb_stat: {self.rb_stat})"
            )

        current_time = datetime.now(timezone.utc).strftime(r"%Y%m%d_%H%M%S")
        calib_log_path_overwrite = os.path.join(
            self.rb.work_dir, "logs", f"calibration_{current_time}.log"
        )
        self.calib_log = LogParser(path=calib_log_path_overwrite)

        print(f"Running calibration, will log to: {repr(self.calib_log.path)}")
        cmd = [
            "calibration",
            str(self.rb.calib_config_file),
            "--log_path_overwrite",
            self.calib_log.path,
        ]
        if worker_name:
            cmd.extend(["--worker_name", worker_name])
        print(f"Running command args: {cmd}")
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=quit_calibration_after_duration,
                check=True,
            )
        except subprocess.TimeoutExpired as e:
            if not quit_calibration_after_duration:
                raise e
            stderr_str = e.stderr.decode()
        except subprocess.CalledProcessError as e:
            print(f"Calibration failed with exception {type(e)}: {repr(e)}.")
            self.fcst_exe_stat = TestStat.FAIL
            self.fcst_exe_excep = e
            self.fcst_exe_excep_tb = traceback.format_exc().splitlines()
            stderr_str = e.stderr.decode()
        else:
            self.fcst_exe_stat = TestStat.PASS
            stderr_str = proc.stderr.decode()
        self.calib_proc_stderr = stderr_str.splitlines()
        if os.path.exists(self.calib_log.path):
            self.calib_log.read_and_parse()

    def execute_forecast(
        self,
        quit_forecast_after_forcing_running: bool,
        quit_forecast_after_duration: float | None,  # seconds
    ) -> None:
        """Run the forecast, optionally quitting after forcing has begun,
        optionally quitting after a certain duration in seconds"""
        if self.rb_stat != TestStat.PASS:
            raise RuntimeError(
                f"Cannot run forecast when realization did not build (self.rb_stat: {self.rb_stat})"
            )

        if quit_forecast_after_forcing_running:
            assert quit_forecast_after_duration is None
            async_waiter = functools.partial(self.wait_for_forcing_is_running)

        elif quit_forecast_after_duration is not None:
            assert not quit_forecast_after_forcing_running
            async_waiter = functools.partial(
                self.wait_for_duration, wait_duration_sec=quit_forecast_after_duration
            )

        else:
            async_waiter = None

        try:
            config_cache = ConfigCache(self.rb.valid_yaml)
            with ForecastExecutionManager(
                valid_yaml=self.rb.valid_yaml,
                real_path=str(self.rb.realization_file),
                config_cache=config_cache,
            ) as self.fcst_exe_mgr:
                self.fcst_exe_mgr.preprocess()
                if async_waiter:
                    # When wait=false, user polling is required
                    self.fcst_exe_mgr.execute(wait=False, log_file_open_mode="w")
                    async_waiter()
                else:
                    self.fcst_exe_mgr.execute(wait=True, log_file_open_mode="w")
        except KeyboardInterrupt as e:
            print("Caught KeyboardInterrupt in main thread. Reraising.")
            raise e
        except NgenIntentionallyStoppedError as e:
            # Raised when stop flag is manually set, or when context manager ends before ngen finishes.
            # The latter is happening intentionally here under certain types of tests.
            print(
                f"Caught NgenIntentionallyStoppedError in main thread. Not reraising: {e}"
            )
            fcst_exe_excep = None
        except Exception as e:
            print(
                f"Caught unexpected exception in main thread while executing forecast: {type(e)}: {repr(e)}. Storing exception info in test object to signify failure. Not reraising.\nTraceback was: {traceback.format_exc()}"
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
            if not self.exe_log.fatal_lines:  # and (not self.ngen_log.fatal_lines):  ### TODO update ngen_log to work with new EWTS per-rank logs, and new RTE log paths
                self.fcst_exe_stat = TestStat.PASS
            else:
                self.fcst_exe_stat = TestStat.FAIL
        else:
            self.fcst_exe_excep_type = str(type(self.fcst_exe_excep))
            self.fcst_exe_excep_msg = str(self.fcst_exe_excep)
            self.fcst_exe_stat = TestStat.FAIL

    def read_logs(self) -> None:
        """Read and parse the log files"""
        self.exe_log.read_and_parse()
        # self.ngen_log.read_and_parse()  ### TODO update ngen_log to work with new EWTS per-rank logs, and new RTE log paths

    def wait_for_duration(self, wait_duration_sec: float):
        """Asynchronous loop while ngen in running. Stop ngen after wait_duration_sec seconds."""
        start = time.perf_counter()
        poll_freq_seconds = 2
        print(
            f"Polling ngen process every {poll_freq_seconds} seconds up to {wait_duration_sec} sec total duration..."
        )
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
        """Loop until log file indicates that the forcing engine is running."""
        start = time.perf_counter()
        poll_freq_seconds = 10
        print(f"Polling ngen process every {poll_freq_seconds} seconds...")
        while True:
            duration_sec = time.perf_counter() - start
            self.fcst_exe_mgr.poll_ngen_flush_log()
            if duration_sec > 10 and self.infer_from_log__forcing_is_running():
                print(
                    f"After {duration_sec:.1f} seconds, ngen log indicates forcing is running successfully"
                )
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
        raise NotImplementedError(
            "TODO update ngen_log to work with new EWTS per-rank logs, and new RTE log paths"
        )
        if os.path.exists(self.ngen_log.path):
            self.ngen_log.read_and_parse()
        else:
            print(f"Does not exist yet: {self.ngen_log.path}")
            return False
        # TODO improve this and confirm that it works for types other than short_range
        if (
            self.ngen_log.content.lower().count("processing forecast cycle") > 1
            and self.ngen_log.content.lower().count(
                "writing output forcing file for timestamp"
            )
            > 0
        ):
            return True
        else:
            return False


class TestResultsSums(BaseModel):
    """Helper class for running a managed set of test realizations."""

    rb_statcount: dict[str, int]  # Status counts for RealizationBuilder events
    fcst_exe_statcount: dict[str, int]  # Status counts for forecast execution events
    any_failed: bool = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        self.any_failed = (
            True
            if (
                self.rb_statcount[TestStat.FAIL]
                or self.fcst_exe_statcount[TestStat.FAIL]
            )
            else False
        )


class TestsManager(BaseModel):
    """Helper class for running a managed set of test realizations."""

    restart: bool
    prev_results: list[dict] = Field(default_factory=list)
    """If using restart, the initial elements will be dicts parsed from previous run"""
    forecast_tests: list[ForecastTest] = Field(default_factory=list)

    @validate_call
    def add_forecast_test(self, t: ForecastTest) -> None:
        self.forecast_tests.append(t)

    def model_post_init(self, __context):
        prev_results = []
        if os.path.exists(c.TEST_RESULTS_FILE):
            if self.restart:
                print(f"restart={self.restart}, reading: {c.TEST_RESULTS_FILE}")
                with open(c.TEST_RESULTS_FILE) as f:
                    content = f.read()
                rows = json.loads(content) if content else []
                for row in rows:
                    prev_results.append(row)
            else:
                print(f"restart={self.restart}, deleting: {c.TEST_RESULTS_FILE}")
                os.remove(c.TEST_RESULTS_FILE)
        self.prev_results = prev_results

    @property
    def fcst_stat_sums(self) -> TestResultsSums:
        """Build and return a TestResultsSums instance, to assist with evaluating test results."""
        # Initialize these to 0 count for each status option, then increment based on result from tests.
        rb_statcount = {str(status): 0 for status in TestStat}
        fcst_exe_statcount = {str(status): 0 for status in TestStat}
        for t in self.prev_results:
            rb_statcount[t["rb_stat"]] += 1
            fcst_exe_statcount[t["fcst_exe_stat"]] += 1
        for t in self.forecast_tests:
            rb_statcount[str(getattr(t, "rb_stat"))] += 1
            fcst_exe_statcount[str(getattr(t, "fcst_exe_stat"))] += 1

        return TestResultsSums(
            rb_statcount=rb_statcount,
            fcst_exe_statcount=fcst_exe_statcount,
        )

    @property
    def concatenated_results_dicts(self) -> list[dict]:
        new_results = json.loads(
            json.dumps(self.forecast_tests, default=pydantic_encoder)
        )
        concat_results = self.prev_results + new_results
        return concat_results

    def evaluate_test_results(self, raise_if_any_failed: bool = True) -> None:
        """Inspect the test results json file, and if any failed, raise an error."""
        msg = f"\n\n###### FORECAST TEST RESULTS ######\nWriting to: {c.TEST_RESULTS_FILE}\n{json.dumps(self.fcst_stat_sums, indent=2, default=pydantic_encoder)}"
        print(msg)
        with open(c.TEST_RESULTS_FILE, "w") as f:
            f.write(json.dumps(self.concatenated_results_dicts, indent=2))
        if raise_if_any_failed and self.fcst_stat_sums.any_failed:
            raise RuntimeError(self.fcst_stat_sums)
