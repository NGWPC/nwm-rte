import argparse
from datetime import datetime
import functools

from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

import utils_testing_setup
from execution_tests import (
    TestStat,
    LogParser,
    ForecastTest,
    TestsManager,
    get_test_configs__forecast,
    get_test_configs__calibration,
    FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT,
    DEFAULT_GAGE_ID,
    DEFAULT_FORCING_PROVIDER,
    DEFAULT_FORECAST_RUN_NAME,
    FORMULATION_NAME,
    DEFAULT_MAIN_DIR,
    CALIB_OBJECTIVE_FUNCTION,
    CALIB_OPTIMIZATION_ALGO,
    DEFAULT_NPROCS,
    make_parallel_config,
)
from pseudocode import SavedState_Pseudo, StateManager_Pseudo

print = functools.partial(print, flush=True)


TEST_DIR_BASE = f"{DEFAULT_MAIN_DIR}/{CALIB_OBJECTIVE_FUNCTION}_{CALIB_OPTIMIZATION_ALGO}/{FORMULATION_NAME}/{DEFAULT_GAGE_ID}"
# TEST_DIR_INPUT = f"{TEST_DIR_BASE}/Input"
TEST_DIR_OUTPUT = f"{TEST_DIR_BASE}/Output"
# TEST_NGEN_LOG_FILE = f"{TEST_DIR_BASE}/logs/ngen.log"

### Read by build_calib_realization()
# CALIB_CONFIG_FILE = f"{DEFAULT_MAIN_DIR}/cold_start_workflow/input_calibration_{DEFAULT_FORCING_PROVIDER}.config"
# CALIB_CONFIG_FILE = f"{DEFAULT_MAIN_DIR}/cold_start_workflow/input_calibration_{DEFAULT_FORCING_PROVIDER}_short.config"

### Read by build_fcst_realization() for CS and for Forecast
# FORECAST_CONFIG_FILE = f"{DEFAULT_MAIN_DIR}/cold_start_workflow/input_forecast.config"
FORECAST_VALID_YAML = f"{TEST_DIR_OUTPUT}/Validation_Run/{DEFAULT_GAGE_ID}_config_valid_best.yaml"


def calibrations__build_and_run(test_manager: TestsManager, nprocs: int) -> None:
    """Build calibration realizations and run them as tests."""
    for config_overrides in get_test_configs__calibration(nprocs=nprocs):
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

        test_manager.add_forecast_test(t)


def forecasts__build_and_run(
    test_manager: TestsManager,
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
    test_manager is modified in-place, so some test results may be available if this function is interrupted.
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
            # "input_path": FORECAST_CONFIG_FILE,
            "valid_yaml": FORECAST_VALID_YAML,
            "fcst_run_name": fcst_run_name,
            "config_overrides": config_overrides,
            "use_cold_start": do_coldstart,
        }
        print(f"\n\n##########\n### {fc}: setting up test with rb_kwargs = {rb_kwargs}")

        t = ForecastTest(
            rb_kwargs=rb_kwargs,
            ngen_log=LogParser(path=f"{TEST_DIR_OUTPUT}/Forecast_Run/{fcst_run_name}/logs/ngen.log"),
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

        test_manager.add_forecast_test(t)


def main(
    delete_scratch_and_mesh_first: bool,
    skip_forecast: bool,
    quit_forecast_after_forcing_running: bool,
    quit_forecast_after_duration: float | None,
    do_calibration: bool,
    do_all_forcing_configs: bool,
    do_coldstart: bool,
    fcst_run_name: str,
    nprocs: int,
):
    if not fcst_run_name.strip():
        raise ValueError(f"Empty fcst_run_name: {repr(fcst_run_name)}")
    if skip_forecast:
        if do_all_forcing_configs:
            raise ValueError(
                f"Cannot use skip_forecast={skip_forecast} and do_all_forcing_configs={do_all_forcing_configs}"
            )
        if do_coldstart:
            raise ValueError(f"Cannot use skip_forecast={skip_forecast} and do_coldstart={do_coldstart}")

    utils_testing_setup.assert_paths__core(DEFAULT_GAGE_ID)
    # utils_testing_setup.assert_paths__raw_config(CALIB_CONFIG_FILE, FORECAST_CONFIG_FILE)

    # TODO pseudocode for now for states.
    state_manager = StateManager_Pseudo()
    tests_manager = TestsManager()

    ### NOTE this deletes the test output dir.
    ### If wanting to skip Calibration but still do CS and/or Forecast,
    ### then remove this line so that the test calibration results remain available.
    # utils_testing_setup.delete_test_output_dir(TEST_DIR_OUTPUT)

    if delete_scratch_and_mesh_first:
        utils_testing_setup.delete_files_to_force_esmf_and_netcdf_actions(DEFAULT_GAGE_ID)

    if do_calibration:
        calibrations__build_and_run(tests_manager, nprocs)

    if not skip_forecast:
        forecasts__build_and_run(
            tests_manager,
            state_manager,
            do_all_forcing_configs,
            quit_forecast_after_forcing_running,
            quit_forecast_after_duration,
            do_coldstart,
            fcst_run_name,
            # nprocs,
        )

    tests_manager.evaluate_test_results()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--delete_scratch_and_mesh_first",
        action="store_true",
        help="Delete some files before the runs, which forces ESMF and NetCDF actions to occur, for testing those.",
    )
    parser.add_argument(
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
        "--quit_forecast_after_duration",
        default=None,
        type=float,
        help="Instead of waiting for each forecast to finish, quit after the specified elapsed processing duration in seconds.",
    )
    parser.add_argument(
        "--do_calibration",
        action="store_true",
        help="Build and run calibration before forecasts",
    )
    parser.add_argument(
        "--do_all_forcing_configs",
        action="store_true",
        help=f"Run all forcing configurations rather than the default shorter default list. Default list: {FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT}. Incompatible with --skip_forecast.",
    )
    parser.add_argument(
        "--do_coldstart",
        action="store_true",
        help="Causes use_cold_start to be True for all forecasts",
    )
    parser.add_argument(
        "--fcst_run_name",
        type=str,
        default=DEFAULT_FORECAST_RUN_NAME,
        help=f"Replaces default value for fcst_run_name ({repr(DEFAULT_FORECAST_RUN_NAME)})",
    )
    parser.add_argument(
        "--nprocs",
        type=int,
        default=DEFAULT_NPROCS,
        help=f"""
Currently only affects Calibration. Replaces default value for nprocs ({repr(DEFAULT_NPROCS)}) and subsequently the ParallelConfig instance.
When nprocs is 1, Calibration's ParallelConfig is: {make_parallel_config(nprocs=1)}.
When nprocs > 1, Calibration's ParallelConfig is like: {make_parallel_config(nprocs=2)}
""",
    )
    args = parser.parse_args()
    print(f"args: {args}")
    main(**vars(args))
