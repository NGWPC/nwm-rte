"""Test logic for iteating over various forecast and calibration realiztion types, trapping errors and writing results to a json file"""

import functools
import itertools
import json
import os
import subprocess
import traceback
from datetime import datetime, timezone
from enum import StrEnum

import pandas as pd
from mswm.build_inputs import RealizationBuilder
from mswm.utils.input_configuration import ForcingConfig, InputConfig
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT as DDF
from nwm_fcst_mgr.exceptions import NgenIntentionallyStoppedError
from nwm_fcst_mgr.forecast import ForecastExecutionManager
from pydantic import BaseModel, ConfigDict, Field, RootModel, validate_call

from ngen_rte import consts as c
from ngen_rte import run_calibration
from ngen_rte.configs import (
    ModelFormulation,
    RTECalibConfig,
    RTETestConfig,
    make_parallel_config,
)
from ngen_rte.execution.ngen_async import NgenRunnerAsync
from ngen_rte.execution.ngen_logs import TestLines, _LogParserGeneric
from ngen_rte.logger import initialize_logger
from ngen_rte.utils import build_realization

LOG = initialize_logger()


def get_test_configs__calibration(
    cfg: RTETestConfig,
    obj_func: c.CalObjective = c.CALIB_OBJECTIVE_FUNCTION,
    optim_algo: c.CalOptimizationAlgo = c.CALIB_OPTIMIZATION_ALGO,
) -> list[RTECalibConfig]:
    """Build and return a list of InputConfig instances to be used for building calibration realizations.
    If the model_formulations_file is provided, it will be parsed to determine which formulations to run.
    Otherwise, the default formulation from consts.DEFAULT_MODEL_FORMULATION_ARGS will be ran."""
    if cfg.model_formulations_file:
        model_formulations = build_model_formulations_for_test(
            cfg.model_formulations_file
        )
    elif cfg.model_formulation is not None:
        model_formulations = [cfg.model_formulation]
    else:
        model_formulations = [ModelFormulation(*c.DEFAULT_MODEL_FORMULATION_ARGS)]

    calib_configs: list[RTECalibConfig] = []

    for mf, fct in itertools.product(
        model_formulations, cfg.calibration_forcing_sources
    ):
        parser = run_calibration.cli_arg_parser()
        args = parser.parse_args(
            [
                "--objective_function",
                f"{obj_func.value}",
                "--optimization_algorithm",
                f"{optim_algo.value}",
                "--forcing_configuration",
                f"{fct}",
                "--model-formulation",
                f"{mf.models_csv}",
                "--root-zone",
                f"{mf.cfe_aet_rootzone}",
                "--hydrofab_file",
                "/s3/ngwpc-dev/rte-test-data/gages/gauge_01123000.gpkg",
            ]
        )
        calib_config = RTECalibConfig(**vars(args))
        calib_configs.append(calib_config)

    return calib_configs


def get_test_configs__forecast(
    cfg: RTETestConfig,
    use_cold_start: bool = False,
) -> list[InputConfig]:
    """Build and return a list of InputConfig instances to be used for building forecast realizations."""
    configs: list[InputConfig] = []

    if use_cold_start:
        cold_start_datetime = c.DT_START_COLDSTART.strftime(DDF)
        cycle_datetime = c.DT_END_COLDSTART.strftime(DDF)
    else:
        cold_start_datetime = None
        cycle_datetime = c.DT_START_FORECAST.strftime(DDF)

    if cfg.do_all_forcing_configs:
        forcing_config_types = c.FORECAST_FORCING_TYPES
    else:
        forcing_config_types = c.FORECAST_FORCING_TYPES__TESTS

    for fct in forcing_config_types:
        general = None
        forcing = ForcingConfig(
            forcing_provider=c.FORCING_PROVIDER,
            forcing_dir=cfg.forcing_static_dir,
            forcing_template_dir=c.FORCING_TEMPLATE_DIR,
            root_dir=c.FORCING_ROOT_DIR,
            forcing_configuration=fct,
            cycle_datetime=cycle_datetime,
            cold_start_datetime=cold_start_datetime,
            scratch_dir_override=c.SCRATCH_DIR_OVERRIDE,
            forcing_product_versions=c.FORCING_PRODUCT_VERSIONS_DICT,
        )
        parallel = make_parallel_config(cfg.nprocs)
        configs.append(InputConfig(General=general, Forcing=forcing, Parallel=parallel))

    return configs


def build_model_formulations_for_test(
    model_formulations_file: str | None = None,
) -> list[ModelFormulation]:
    """If model_formulations_file is provided, then parse it to return a list of ModelFormulation instance.
    Otherwise, return a list of length 1 using consts.DEFAULT_MODEL_FORMULATION_ARGS"""
    model_formulations = []

    if model_formulations_file is None:
        model_formulations.append(ModelFormulation(*c.DEFAULT_MODEL_FORMULATION_ARGS))
    else:
        LOG.info(f"Reading: {model_formulations_file}")
        if not model_formulations_file.endswith(".tsv"):
            raise ValueError(
                f"Expected model_formulations_file to end with .tsv (indicating tab-separated values) but received: {model_formulations_file}"
            )
        df = pd.read_csv(model_formulations_file, sep="\t")
        for i, row in df.iterrows():
            formulation_csv = row["formulation_mswm"]
            rz_raw = row["uses_root_zone"]
            if str(rz_raw).lower().strip() in ("true", "1", "yes"):
                rz = True
            elif str(rz_raw).lower().strip() in ("false", "0", "no"):
                rz = False
            else:
                raise ValueError(
                    f"Unexpected value for uses_root_zone of row {i} of file {model_formulations_file}: {row}"
                )

            # # NOTE for testing a small batch
            # if len(model_formulations) > 2:
            #     break
            # if rz is not True:
            #     continue

            model_formulations.append(ModelFormulation(formulation_csv, rz))

    return model_formulations


class TestStat(StrEnum):
    """Status enumerator for test execution"""

    NOSTATUS = "NOSTATUS"
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


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

    log2testlines: dict[str, TestLines] = Field(init=False, default_factory=dict)
    # Stderr lines of the subprocess call to calibration executable.
    calib_proc_stderr: list[str] = Field(init=False, default=[])

    def make_realization_builder__build_realization(self, build_method: str) -> None:
        """Instantiate the RealizationBuilder class and build the realization.
        build_method must be a valid build_method of RealizationBuilder, e.g. 'build_fcst_realization' or 'build_calibration_realization'.
        """
        try:
            self.rb = build_realization(self.rb_kwargs, build_method=build_method)
        except Exception as e:
            LOG.info(
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
        self.calib_log = _LogParserGeneric(log_file_path=calib_log_path_overwrite)

        LOG.info(
            f"Running calibration, will log to: {repr(self.calib_log.log_file_path)}"
        )
        cmd = run_calibration.get_calibration_cmd(
            self.rb, worker_name, self.calib_log.log_file_path
        )
        LOG.info(f"Running command args: {cmd}")
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
            if e.stderr is not None:
                stderr_str = e.stderr.decode()
            else:
                stderr_str = ""
        except subprocess.CalledProcessError as e:
            LOG.info(f"Calibration failed with exception {type(e)}: {repr(e)}.")
            self.fcst_exe_stat = TestStat.FAIL
            self.fcst_exe_excep = e
            self.fcst_exe_excep_tb = traceback.format_exc().splitlines()
            if e.stderr is not None:
                stderr_str = e.stderr.decode()
            else:
                stderr_str = ""
        else:
            self.fcst_exe_stat = TestStat.PASS
            stderr_str = proc.stderr.decode()
        self.calib_proc_stderr = stderr_str.splitlines()
        if os.path.exists(self.calib_log.log_file_path):
            self.calib_log.read_and_parse_all_lines_for_issues()
        # TODO set status based on log lines parsed?

    def execute_forecast(self, quit_forecast_after_duration: float | None) -> None:
        """Run the forecast, optionally quitting after forcing has begun,
        optionally quitting after quit_forecast_after_duration in seconds"""
        if self.rb_stat != TestStat.PASS:
            raise RuntimeError(
                f"Cannot run forecast when realization did not build (self.rb_stat: {self.rb_stat})"
            )

        ngen_runner = NgenRunnerAsync(
            rb=self.rb,
            postprocess=True,
            suppress_output=False,
            timeout_secs=quit_forecast_after_duration,
        )
        try:
            ngen_runner.start()
            ngen_runner.stream_status_until_complete()
        except KeyboardInterrupt as e:
            LOG.info("Caught KeyboardInterrupt in main thread. Reraising.")
            raise e
        except NgenIntentionallyStoppedError as e:
            # Raised when stop flag is manually set, or when context manager ends before ngen finishes.
            # The latter is happening intentionally here under certain types of tests.
            LOG.info(
                f"Caught NgenIntentionallyStoppedError in main thread. Not reraising: {e}"
            )
            fcst_exe_excep = None
        except Exception as e:
            LOG.info(
                f"Caught unexpected exception in main thread while executing forecast: {type(e)}: {repr(e)}. Storing exception info in test object to signify failure. Not reraising.\nTraceback was: {traceback.format_exc()}"
            )
            fcst_exe_excep = e
            self.fcst_exe_excep_tb = traceback.format_exc().splitlines()
        else:
            fcst_exe_excep = None
            self.fcst_exe_excep_tb = []
        finally:
            ngen_runner.close()

        self.fcst_exe_excep = fcst_exe_excep

        for lp in ngen_runner.log_parsers:
            lp.read_and_parse_all_lines_for_issues()
            self.log2testlines.update(lp.log2testlines)

        if self.fcst_exe_excep is None:
            self.fcst_exe_excep_type = None
            self.fcst_exe_excep_msg = None
            if any(
                self.log2testlines[log_file].fatal_lines
                for log_file in self.log2testlines
            ):
                # TODO also consider if SEVER and CRITICAL warrant a FAIL.
                self.fcst_exe_stat = TestStat.FAIL
            else:
                self.fcst_exe_stat = TestStat.PASS
        else:
            self.fcst_exe_excep_type = str(type(self.fcst_exe_excep))
            self.fcst_exe_excep_msg = str(self.fcst_exe_excep)
            self.fcst_exe_stat = TestStat.FAIL


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
                LOG.info(f"restart={self.restart}, reading: {c.TEST_RESULTS_FILE}")
                with open(c.TEST_RESULTS_FILE) as f:
                    content = f.read()
                rows = json.loads(content) if content else []
                for row in rows:
                    prev_results.append(row)
            else:
                LOG.info(f"restart={self.restart}, deleting: {c.TEST_RESULTS_FILE}")
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
        new_results = json.loads(RootModel(self.forecast_tests).model_dump_json())
        concat_results = self.prev_results + new_results
        return concat_results

    def evaluate_test_results(self, raise_if_any_failed: bool = True) -> None:
        """Inspect the test results json file, and if any failed, raise an error."""
        msg = f"\n\n###### FORECAST TEST RESULTS ######\nWriting to: {c.TEST_RESULTS_FILE}\n{self.fcst_stat_sums.model_dump_json(indent=2)}"
        LOG.info(msg)
        with open(c.TEST_RESULTS_FILE, "w") as f:
            f.write(json.dumps(self.concatenated_results_dicts, indent=2))
        if raise_if_any_failed and self.fcst_stat_sums.any_failed:
            raise RuntimeError(self.fcst_stat_sums)
