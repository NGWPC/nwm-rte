import argparse
from datetime import datetime
import functools
import json

from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

import utils_testing_setup
from execution_tests import (
    TestPaths,
    TestStat,
    LogParser,
    ForecastTest,
    TestsManager,
    get_test_configs__forecast,
    get_test_configs__calibration,
    make_parallel_config,
)
from pseudocode import SavedState_Pseudo, StateManager_Pseudo
from pydantic import BaseModel, ConfigDict, Field, validate_call
from pydantic.json import pydantic_encoder

import consts as c

print = functools.partial(print, flush=True)


class Config(BaseModel):
    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    delete_scratch_and_mesh_first: bool
    delete_forcing_raw_input_first: bool
    skip_forecast: bool
    quit_forecast_after_forcing_running: bool
    quit_forecast_after_duration: float | None = Field(ge=0)
    do_calibration: bool
    do_all_forcing_configs: bool
    do_coldstart: bool
    fcst_run_name: str
    nprocs: int = Field(ge=1)
    gage_id__gage_vintage: list[str] = Field(min_length=2, max_length=2)

    # Set after init
    gage_id: str = Field(init=False, default=None)
    gage_vintage: str = Field(init=False, default=None)
    tests_manager: TestsManager = Field(init=False, default=None)
    state_manager: StateManager_Pseudo = Field(init=False, default=None)  # TODO pseudocode for now for states.
    test_paths: TestPaths = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        errors = []

        gage_id, gage_vintage = self.gage_id__gage_vintage
        if gage_id != gage_id.strip():
            errors.append(ValueError(f"Whitespace found on end of gage_id: {repr(gage_id)}"))
        if gage_vintage != gage_vintage.strip():
            errors.append(ValueError(f"Whitespace found on end of gage_vintage: {repr(gage_vintage)}"))

        if self.fcst_run_name != self.fcst_run_name.strip():
            errors.append(ValueError(f"Whitespace found on end of fcst_run_name: {repr(self.fcst_run_name)}"))

        if self.do_all_forcing_configs:
            if self.skip_forecast and (not self.do_coldstart):
                errors.append(
                    ValueError(
                        f"When do_all_forcing_configs={self.do_all_forcing_configs}, must have coldstart and/or forecast enabled."
                    )
                )

        if errors:
            raise RuntimeError(errors)

        self.gage_id = gage_id
        self.gage_vintage = gage_vintage
        self.tests_manager = TestsManager()
        self.state_manager = StateManager_Pseudo()
        self.test_paths = TestPaths(
            gage_id=gage_id,
            gage_vintage=gage_vintage,
            obj_func=c.CALIB_OBJECTIVE_FUNCTION,
            optim_algo=c.CALIB_OPTIMIZATION_ALGO,
        )


def calibrations__build_and_run(cfg: Config) -> None:
    """Build calibration realizations and run them as tests."""
    for config_overrides in get_test_configs__calibration(
        nprocs=cfg.nprocs,
        gage_id=cfg.gage_id,
        gage_vintage=cfg.gage_vintage,
    ):
        fc = config_overrides.Forcing.forcing_configuration
        rb_kwargs = {"config_overrides": config_overrides}
        print(f"\n\n##########\n### Calibration {repr(fc)}: setting up test with rb_kwargs = \n{json.dumps(rb_kwargs, indent=2, default=pydantic_encoder)}")
        t = ForecastTest(rb_kwargs=rb_kwargs)

        # Build the realization, trapping exceptions into class attrs
        print(f"### Calibration {repr(fc)}: building realization")
        t.make_realization_builder__build_realization(build_method="build_calib_realization")

        if t.rb_stat == TestStat.PASS:
            # Execute the realization via ngen, trapping exceptions and logs into class attrs
            print(f"### Calibration {repr(fc)}: executing calibration realization")
            t.execute_calibration()

        cfg.tests_manager.add_forecast_test(t)


def forecasts__build_and_run(cfg: Config, cs: bool) -> None:
    """
    Using ForecastTest, build and execute a list of forecast realizations.
    tests_manager is modified in-place, so some test results may be available if this function is interrupted.
    `cs` controls whether coldstart is used (not `cfg.do_coldstart`).
    """
    test_configs = get_test_configs__forecast(cfg.do_all_forcing_configs, use_cold_start=cs)
    for tc in test_configs:
        if cfg.quit_forecast_after_forcing_running and tc.Forcing.forcing_configuration != "short_range":
            raise NotImplementedError(
                f"quit_forecast_after_forcing_running not yet tested for forcing_configuration = {repr(tc.Forcing.forcing_configuration)}"
            )

    for config_overrides in test_configs:
        fc = config_overrides.Forcing.forcing_configuration
        rb_kwargs = {
            # "input_path": cfg.test_paths.dir_input,
            "valid_yaml": cfg.test_paths.valid_yaml,
            "fcst_run_name": cfg.fcst_run_name,
            "config_overrides": config_overrides,
            "use_cold_start": cs,
        }
        print(f"\n\n##########\n### Forecast {repr(fc)}: setting up test with rb_kwargs = {rb_kwargs}")

        t = ForecastTest(
            rb_kwargs=rb_kwargs,
            ngen_log=LogParser(path=f"{cfg.test_paths.dir_output}/Forecast_Run/{cfg.fcst_run_name}/logs/ngen.log"),
        )

        # Build the realization, trapping exceptions into class attrs
        print(f"### Forecast {repr(fc)}: building realization")
        t.make_realization_builder__build_realization(build_method="build_fcst_realization")

        if t.rb_stat == TestStat.PASS:
            # Execute the realization via ngen, trapping exceptions and logs into class attrs
            print(f"### Forecast {repr(fc)}: executing realization via ngen")
            t.execute_forecast(
                quit_forecast_after_forcing_running=cfg.quit_forecast_after_forcing_running,
                quit_forecast_after_duration=cfg.quit_forecast_after_duration,
            )

            if t.rb.input_configs_class.Forcing.forcing_configuration == "standard_ana":
                cfg.state_manager.add_saved_state(
                    SavedState_Pseudo(
                        dt=datetime.strptime(t.rb.input_configs_class.Forcing.cycle_datetime, DEFAULT_DATETIME_FORMAT),
                        realization_file=t.rb.realization_file,
                    )
                )

        cfg.tests_manager.add_forecast_test(t)


@validate_call
def main(cfg: Config):
    utils_testing_setup.assert_paths__core(cfg.test_paths)
    # utils_testing_setup.assert_paths__raw_config(cfg.test_paths)  # Only works for default gage
    ### NOTE this deletes the test output dir.
    ### If wanting to skip Calibration but still do CS and/or Forecast,
    ### then remove this line so that the test calibration results remain available.
    # utils_testing_setup.delete_test_output_dir(cfg.test_paths)

    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg.test_paths)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()

    if cfg.do_calibration:
        calibrations__build_and_run(cfg)

    if cfg.do_coldstart:
        forecasts__build_and_run(cfg, cs=True)
    if not cfg.skip_forecast:
        forecasts__build_and_run(cfg, cs=False)

    cfg.tests_manager.evaluate_test_results()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-delscratch",
        "--delete_scratch_and_mesh_first",
        action="store_true",
        help="Delete scratch dir and ESMF mesh files before the run, which forces ESMF and NetCDF actions to occur.",
    )
    parser.add_argument(
        "-delraw",
        "--delete_forcing_raw_input_first",
        action="store_true",
        help=f"Delete contents of {repr(c.DIR_FORCING_RAW_INPUT)} before the run, which forces forcing data to be re-downloaded.",
    )
    parser.add_argument(
        "-nofcst",
        "--skip_forecast",
        action="store_true",
        help=f"Skip building and running forecasts. Incompatible with --do_all_forcing_configs and --do_coldstart",
    )
    parser.add_argument(
        "--quit_forecast_after_forcing_running",
        action="store_true",
        help="Instead of waiting for each forecast to finish, quit after the ngen log file indicates that forcing is running successfully.",
    )
    parser.add_argument(
        "-dur",
        "--quit_forecast_after_duration",
        default=None,
        type=float,
        help="Instead of waiting for each forecast to finish, quit after the specified elapsed processing duration in seconds.",
    )
    parser.add_argument(
        "-calib",
        "--do_calibration",
        action="store_true",
        help="Build and run calibration before forecasts",
    )
    parser.add_argument(
        "-allforcings",
        "--do_all_forcing_configs",
        action="store_true",
        help=f"Run all forcing configurations rather than the default shorter default list. Default list: {c.FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT}. Incompatible with --skip_forecast.",
    )
    parser.add_argument(
        "-cs",
        "--do_coldstart",
        action="store_true",
        help="Causes use_cold_start to be True for all forecasts",
    )
    parser.add_argument(
        "-fcname",
        "--fcst_run_name",
        type=str,
        default=c.DEFAULT_FORECAST_RUN_NAME,
        help=f"Replaces default value for fcst_run_name ({repr(c.DEFAULT_FORECAST_RUN_NAME)})",
    )
    parser.add_argument(
        "-n",
        "--nprocs",
        type=int,
        default=c.DEFAULT_NPROCS,
        help=f"""
Currently only affects Calibration. Replaces default value for nprocs ({repr(c.DEFAULT_NPROCS)}) and subsequently the ParallelConfig instance.
When nprocs is 1, Calibration's ParallelConfig is: {make_parallel_config(nprocs=1)}.
When nprocs > 1, Calibration's ParallelConfig is like: {make_parallel_config(nprocs=2)}
""",
    )
    parser.add_argument(
        "-g",
        "--gage_id__gage_vintage",
        type=str,
        nargs=2,
        default=[c.DEFAULT_GAGE_ID, c.DEFAULT_GAGE_VINTAGE],
        help=f"Calibration gage ID and gage vintage (2 args). If not provided, then these defaults will be used: {c.DEFAULT_GAGE_ID}, {c.DEFAULT_GAGE_VINTAGE} will be used.",
    )
    args = parser.parse_args()
    print(f"{__file__}: args: {json.dumps(vars(args), indent=2)}")

    cfg = Config(**vars(args))
    main(cfg)
