import argparse
from datetime import datetime
import functools

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

import consts as c

print = functools.partial(print, flush=True)


def calibrations__build_and_run(test_paths: TestPaths, tests_manager: TestsManager, nprocs: int) -> None:
    """Build calibration realizations and run them as tests."""
    for config_overrides in get_test_configs__calibration(
        nprocs=nprocs,
        gage_id=test_paths.gage_id,
        gage_vintage=test_paths.gage_vintage,
    ):
        fc = config_overrides.Forcing.forcing_configuration
        rb_kwargs = {"config_overrides": config_overrides}
        print(f"\n\n##########\n### Calibration: {fc}: setting up test with rb_kwargs = {rb_kwargs}")
        t = ForecastTest(rb_kwargs=rb_kwargs)

        # Build the realization, trapping exceptions into class attrs
        print(f"### {fc}: building realization")
        t.make_realization_builder__build_realization(build_method="build_calib_realization")

        if t.rb_stat == TestStat.PASS:
            # Execute the realization via ngen, trapping exceptions and logs into class attrs
            print(f"### {fc}: executing calibration realization")
            t.execute_calibration()

        tests_manager.add_forecast_test(t)


def forecasts__build_and_run(
    test_paths: TestPaths,
    tests_manager: TestsManager,
    state_manager: StateManager_Pseudo,
    do_all_forcing_configs: bool,
    quit_forecast_after_forcing_running: bool,
    quit_forecast_after_duration: float | None,
    do_coldstart: bool,
    fcst_run_name: str,
    # nprocs: int,
) -> None:
    """
    Using ForecastTest, build and execute a list of forecast realizations.
    tests_manager is modified in-place, so some test results may be available if this function is interrupted.
    """
    test_configs = get_test_configs__forecast(do_all_forcing_configs, do_coldstart)
    for tc in test_configs:
        if quit_forecast_after_forcing_running and tc.Forcing.forcing_configuration != "short_range":
            raise NotImplementedError(
                f"quit_forecast_after_forcing_running not yet tested for forcing_configuration = {repr(tc.Forcing.forcing_configuration)}"
            )

    for config_overrides in test_configs:
        fc = config_overrides.Forcing.forcing_configuration
        rb_kwargs = {
            # "input_path": test_paths.dir_input,
            "valid_yaml": test_paths.valid_yaml,
            "fcst_run_name": fcst_run_name,
            "config_overrides": config_overrides,
            "use_cold_start": do_coldstart,
        }
        print(f"\n\n##########\n### {fc}: setting up test with rb_kwargs = {rb_kwargs}")

        t = ForecastTest(
            rb_kwargs=rb_kwargs,
            ngen_log=LogParser(path=f"{test_paths.dir_output}/Forecast_Run/{fcst_run_name}/logs/ngen.log"),
        )

        # Build the realization, trapping exceptions into class attrs
        print(f"### {fc}: building realization")
        t.make_realization_builder__build_realization(build_method="build_fcst_realization")

        if t.rb_stat == TestStat.PASS:
            # Execute the realization via ngen, trapping exceptions and logs into class attrs
            print(f"### {fc}: executing realization via ngen")
            t.execute_forecast(
                quit_forecast_after_forcing_running=quit_forecast_after_forcing_running,
                quit_forecast_after_duration=quit_forecast_after_duration,
            )

            if t.rb.input_configs_class.Forcing.forcing_configuration == "standard_ana":
                state_manager.add_saved_state(
                    SavedState_Pseudo(
                        dt=datetime.strptime(t.rb.input_configs_class.Forcing.cycle_datetime, DEFAULT_DATETIME_FORMAT),
                        realization_file=t.rb.realization_file,
                    )
                )

        tests_manager.add_forecast_test(t)


def main(
    delete_scratch_and_mesh_first: bool,
    delete_forcing_raw_input_first: bool,
    skip_forecast: bool,
    quit_forecast_after_forcing_running: bool,
    quit_forecast_after_duration: float | None,
    do_calibration: bool,
    do_all_forcing_configs: bool,
    do_coldstart: bool,
    fcst_run_name: str,
    nprocs: int,
    gage_id__gage_vintage: list[str],
):

    if not fcst_run_name.strip():
        raise ValueError(f"Empty fcst_run_name: {repr(fcst_run_name)}")
    if do_all_forcing_configs:
        if not (do_coldstart or (not skip_forecast)):
            raise ValueError(
                f"When do_all_forcing_configs={do_all_forcing_configs}, must have coldstart and/or forecast enabled."
            )

    gage_id, gage_vintage = gage_id__gage_vintage
    test_paths = TestPaths(
        gage_id=gage_id,
        gage_vintage=gage_vintage,
        obj_func=c.CALIB_OBJECTIVE_FUNCTION,
        optim_algo=c.CALIB_OPTIMIZATION_ALGO,
    )

    utils_testing_setup.assert_paths__core(test_paths)
    # utils_testing_setup.assert_paths__raw_config(test_paths)  # Only works for default gage

    # TODO pseudocode for now for states.
    state_manager = StateManager_Pseudo()
    tests_manager = TestsManager()

    ### NOTE this deletes the test output dir.
    ### If wanting to skip Calibration but still do CS and/or Forecast,
    ### then remove this line so that the test calibration results remain available.
    # utils_testing_setup.delete_test_output_dir(test_paths)

    if delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(test_paths)
    if delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()

    if do_calibration:
        calibrations__build_and_run(test_paths, tests_manager, nprocs)

    forecast_kwargs_base = {
        "test_paths": test_paths,
        "tests_manager": tests_manager,
        "state_manager": state_manager,
        "do_all_forcing_configs": do_all_forcing_configs,
        "quit_forecast_after_forcing_running": quit_forecast_after_forcing_running,
        "quit_forecast_after_duration": quit_forecast_after_duration,
        "fcst_run_name": fcst_run_name,
        # "nprocs": nprocs,
    }

    if do_coldstart:
        forecasts__build_and_run(**(forecast_kwargs_base | {"do_coldstart": True}))

    if not skip_forecast:
        forecasts__build_and_run(**(forecast_kwargs_base | {"do_coldstart": False}))

    tests_manager.evaluate_test_results()


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
    print(f"args: {args}")
    main(**vars(args))
