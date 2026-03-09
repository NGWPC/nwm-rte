import argparse
from datetime import datetime
import functools
import json
import sys

from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

import utils_testing_setup
from execution_tests import (
    TestStat,
    LogParser,
    ForecastTest,
    TestsManager,
    get_test_configs__forecast,
    get_test_configs__calibration,
    make_parallel_config,
)
from pydantic.json import pydantic_encoder

import consts as c
from configs import RTETestConfig, TestPaths

print = functools.partial(print, flush=True)


def calibrations__build_and_run(cfg: RTETestConfig, tm: TestsManager) -> None:
    """Build calibration realizations and run them as tests."""
    for obj_func, optim_algo, _ in cfg.get_calib_permutations():
        for config_overrides in get_test_configs__calibration(
            nprocs=cfg.nprocs,
            gage_id=cfg.gage_id,
            gage_vintage=cfg.gage_vintage,
            obj_func=obj_func,
            optim_algo=optim_algo,
            global_domain=cfg.global_domain,
            forcing_provider=cfg.forcing_provider,
            forcing_static_dir=cfg.forcing_static_dir,
        ):
            fc = config_overrides.Forcing.forcing_configuration
            msg_prefix = f"Calibration {repr(fc)} with calib obj_func={repr(obj_func.value)}, optim_algo={repr(optim_algo.value)}"
            rb_kwargs = {"config_overrides": config_overrides}
            print(
                f"\n\n##########\n### {msg_prefix}: setting up test with rb_kwargs = \n{json.dumps(rb_kwargs, indent=2, default=pydantic_encoder)}"
            )
            t = ForecastTest(rb_kwargs=rb_kwargs)

            # Build the realization, trapping exceptions into class attrs
            print(f"### {msg_prefix}: building realization")
            t.make_realization_builder__build_realization(
                build_method="build_calib_realization"
            )

            if t.rb_stat == TestStat.PASS:
                # Execute the realization via ngen, trapping exceptions and logs into class attrs
                print(f"### {msg_prefix}: executing calibration realization")
                t.execute_calibration(cfg.quit_calibration_after_duration)

            tm.add_forecast_test(t)


def forecasts__build_and_run(cfg: RTETestConfig, tm: TestsManager, cs: bool) -> None:
    """
    Using ForecastTest, build and execute a list of forecast realizations.
    tests_manager is modified in-place, so some test results may be available if this function is interrupted.
    `cs` controls whether coldstart is used (not `cfg.do_coldstart`).
    """
    for obj_func, optim_algo, test_paths in cfg.get_calib_permutations():
        test_configs = get_test_configs__forecast(
            cfg.do_all_forcing_configs,
            use_cold_start=cs,
            gage_id=cfg.gage_id,
            global_domain=cfg.global_domain,
            forcing_provider=cfg.forcing_provider,
            forcing_static_dir=cfg.forcing_static_dir,
        )
        for tc in test_configs:
            if (
                cfg.quit_forecast_after_forcing_running
                and tc.Forcing.forcing_configuration != "short_range"
            ):
                raise NotImplementedError(
                    f"quit_forecast_after_forcing_running not yet tested for forcing_configuration = {repr(tc.Forcing.forcing_configuration)}"
                )

        for config_overrides in test_configs:
            fc = config_overrides.Forcing.forcing_configuration
            msg_prefix = f"Forecast {repr(fc)} with calib obj_func={repr(obj_func.value)}, optim_algo={repr(optim_algo.value)}"
            rb_kwargs = {
                # "input_path": test_paths.dir_input,
                "valid_yaml": test_paths.valid_yaml,
                "fcst_run_name": cfg.fcst_run_name,
                "config_overrides": config_overrides,
                "use_cold_start": cs,
            }
            print(
                f"\n\n##########\n### {msg_prefix}: setting up test with rb_kwargs = {rb_kwargs}"
            )

            run_type = "Cold_Start_Run" if cs else "Forecast_Run"
            t = ForecastTest(
                rb_kwargs=rb_kwargs,
                ngen_log=LogParser(
                    path=f"{test_paths.dir_output}/{run_type}/{cfg.fcst_run_name}/logs/ngen.log"
                ),
            )

            # Build the realization, trapping exceptions into class attrs
            print(f"### {msg_prefix}: building realization")
            t.make_realization_builder__build_realization(
                build_method="build_fcst_realization"
            )

            if t.rb_stat == TestStat.PASS:
                # Execute the realization via ngen, trapping exceptions and logs into class attrs
                print(f"### {msg_prefix}: executing realization via ngen")
                t.execute_forecast(
                    quit_forecast_after_forcing_running=cfg.quit_forecast_after_forcing_running,
                    quit_forecast_after_duration=cfg.quit_forecast_after_duration,
                )

            tm.add_forecast_test(t)


def run_noop_mode() -> None:
    """Run noop mode - verify imports and basic setup without executing workflows."""
    print("\nRunning in noop mode - only checking imports and basic setup.")
    print("Successfully imported all required libraries.")
    print("Noop mode complete - exiting")
    sys.exit(0)  # Exit the program directly


def main(cfg: RTETestConfig):
    if cfg.noop:
        run_noop_mode()

    utils_testing_setup.assert_paths__core(cfg)
    # utils_testing_setup.assert_paths__raw_config(cfg)
    ### NOTE this deletes the test output dir.
    ### If wanting to skip Calibration but still do CS and/or Forecast,
    ### then remove this line so that the test calibration results remain available.
    # utils_testing_setup.delete_test_output_dir(cfg)

    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()

    tm = TestsManager()

    if cfg.do_calibration:
        calibrations__build_and_run(cfg, tm)

    if cfg.do_coldstart:
        forecasts__build_and_run(cfg, tm, cs=True)
    if not cfg.skip_forecast:
        forecasts__build_and_run(cfg, tm, cs=False)

    tm.evaluate_test_results()


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
        "-quitfcdur",
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
        "-quitcaldur",
        "--quit_calibration_after_duration",
        default=None,
        type=float,
        help="Instead of waiting for each calibration to finish, quit after the specified elapsed processing duration in seconds.",
    )
    parser.add_argument(
        "-ofuncs",
        "--objective_functions",
        nargs="+",
        type=c.CalObjective,
        default=[c.CALIB_OBJECTIVE_FUNCTION],
        help=f"List of objective functions for calibration. Default: {[c.CALIB_OBJECTIVE_FUNCTION]}",
    )
    parser.add_argument(
        "-allofuncs",
        "--do_all_objective_functions",
        action="store_true",
        help=f"For calibration, causes all objective functions to be executed: {list(c.CalObjective)}",
    )
    parser.add_argument(
        "-optalgos",
        "--optimization_algorithms",
        nargs="+",
        type=c.CalOptimizationAlgo,
        default=[c.CALIB_OPTIMIZATION_ALGO],
        help=f"List of optimization algorithms for calibration. Default: {[c.CALIB_OPTIMIZATION_ALGO]}",
    )
    parser.add_argument(
        "-alloptalgos",
        "--do_all_optimization_algorithms",
        action="store_true",
        help=f"For calibration, causes all optimization algorithms to be executed: {list(c.CalOptimizationAlgo)}",
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
    parser.add_argument(
        "-fregion",
        "--global_domain",
        type=str,
        default=c.CALIB_GLOBAL_DOMAIN_DEFAULT,
        choices=c.CALIB_GLOBAL_DOMAIN_CHOICES,
        help=f"Region of forcing data. Default={c.CALIB_GLOBAL_DOMAIN_DEFAULT}",
    )
    parser.add_argument(
        "-fstatic",
        "--forcing_static_dir",
        type=str,
        default=c.FORCING_STATIC_DIR_DEFAULT,
        help=f"Directory for static forcing files, used when forcing_provider is 'bmi'. Default={c.FORCING_STATIC_DIR_DEFAULT}",
    )
    parser.add_argument(
        "-fprovider",
        "--forcing_provider",
        type=str,
        default=c.FORCING_PROVIDER_DEFAULT,
        choices=c.FORCING_PROVIDER_CHOICES,
        help=f"Forcing provider. Default={c.FORCING_PROVIDER_DEFAULT}",
    )
    parser.add_argument(
        "--noop",
        action="store_true",
        help="Run in noop mode - only verify that the script can import libraries and basic setup, then exit without looking for data or running any workflows.",
    )
    args = parser.parse_args()
    print(f"{__file__}: args: {json.dumps(vars(args), indent=2)}")

    cfg = RTETestConfig(**vars(args))
    main(cfg)
