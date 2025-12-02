import argparse
import copy
from datetime import datetime, timedelta
import functools
import json
import os
import subprocess
import typing

from pydantic.json import pydantic_encoder

from mswm.build_inputs import RealizationBuilder
from mswm.utils.input_configuration import (
    InputConfig,
    GeneralConfig,
    ForcingConfig,
)
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

from nwm_fcst_mgr.forecast import run_fcst

import utils_testing_setup
from execution_tests import (
    TestStat,
    LogParser,
    ForecastTest,
    TestsManager,
    get_test_configs__forecast,
    get_test_configs__calibration,
    FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT,
    GAGE_ID,
    FORCING_PROVIDER,
    FORECAST_RUN_NAME,
    FORMULATION_NAME,
    DEFAULT_MAIN_DIR,
    CALIB_OBJECTIVE_FUNCTION,
    CALIB_OPTIMIZATION_ALGO,
    DT_START_FORECAST,
    DT_START_COLDSTART,
    DT_END_COLDSTART,
)
from pseudocode import SavedState_Pseudo, StateManager_Pseudo

print = functools.partial(print, flush=True)


# import logging
# import sys
# logging.basicConfig(
#     level=logging.INFO,
#     handler=logging.StreamHandler(sys.stdout),
#     format="%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s",
# )


TEST_DIR_BASE = f"{DEFAULT_MAIN_DIR}/{CALIB_OBJECTIVE_FUNCTION}_{CALIB_OPTIMIZATION_ALGO}/{FORMULATION_NAME}/{GAGE_ID}"
# TEST_DIR_INPUT = f"{TEST_DIR_BASE}/Input"
TEST_DIR_OUTPUT = f"{TEST_DIR_BASE}/Output"
# TEST_NGEN_LOG_FILE = f"{TEST_DIR_BASE}/logs/ngen.log"
TEST_NGEN_FORECAST_LOG_FILE = f"{TEST_DIR_OUTPUT}/Forecast_Run/{FORECAST_RUN_NAME}/logs/ngen.log"

### Read by build_calib_realization()
CALIB_CONFIG_FILE = f"{DEFAULT_MAIN_DIR}/cold_start_workflow/input_calibration_{FORCING_PROVIDER}.config"
# CALIB_CONFIG_FILE = f"{DEFAULT_MAIN_DIR}/cold_start_workflow/input_calibration_{FORCING_PROVIDER}_short.config"

### Read by build_fcst_realization() for CS and for Forecast
FORECAST_CONFIG_FILE = f"{DEFAULT_MAIN_DIR}/cold_start_workflow/input_forecast.config"
FORECAST_VALID_YAML = f"{TEST_DIR_OUTPUT}/Validation_Run/{GAGE_ID}_config_valid_best.yaml"


DEFAULT_FORECAST_CONFIG = InputConfig(
    Forcing=ForcingConfig(
        forcing_provider=FORCING_PROVIDER,
        forcing_dir=None,
        forcing_template_dir="/ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/",
        root_dir="/ngen-app/data",
        forcing_configuration="short_range",
        cycle_datetime=DT_START_FORECAST.strftime(DEFAULT_DATETIME_FORMAT),
        cold_start_datetime=None,
    )
)

REALIZATION_KWARGS__COLDSTART = {
    "input_path": FORECAST_CONFIG_FILE,  # From disk
    "valid_yaml": FORECAST_VALID_YAML,
    "fcst_run_name": FORECAST_RUN_NAME,
}


def calibrations__build_and_run(test_manager: TestsManager) -> None:
    """Build calibration realizations and run them as tests."""

    # """Build 1 calibration realization and run it."""
    # rb_calib = RealizationBuilder(CALIB_CONFIG_FILE)
    # rb_calib.load_config_apply_overrides()
    # print(f"Building calibration realization: {rb_calib.input_configs_class}")
    # rb_calib.build_calib_realization()
    # if not os.path.isfile(rb_calib.calib_config_file):
    #     raise FileNotFoundError(rb_calib.calib_config_file)
    # print("Running calibration")
    # cmd = [
    #     "python",
    #     "/ngen-app/bin/calibration.py",
    #     str(rb_calib.calib_config_file),
    # ]
    # print(f"Running command args: {cmd}")
    # subprocess.check_call(cmd)

    for config_overrides in get_test_configs__calibration():
        fc = config_overrides.Forcing.forcing_configuration
        rb_kwargs = {"config_overrides": config_overrides}
        print(f"\n\n##########\n### Calibration: {fc}: setting up test with rb_kwargs = {rb_kwargs}")
        t = ForecastTest(rb_kwargs=rb_kwargs, ngen_log=LogParser(path=TEST_NGEN_FORECAST_LOG_FILE))

        # Build the realization, trapping exceptions into class attrs
        print(f"### {fc}: building realization")
        t.make_realization_builder__build_realization(method="build_calib_realization")

        if t.rb_stat == TestStat.PASS:
            # Execute the realization via ngen, trapping exceptions and logs into class attrs
            print(f"### {fc}: executing calibration realization")
            t.execute_calibration()

        test_manager.add_forecast_test(t)


def build_coldstart_realization() -> RealizationBuilder:
    """Build 1 coldstart realization."""
    rb_cs = RealizationBuilder(**REALIZATION_KWARGS__COLDSTART, use_cold_start=True)
    # This can be called before the overrides (InputConfig instance) is defined, to load the .conf file first without overrides.
    # Then overrides can be idiomatically defined by copying the valid config and replacing individual keys.
    # This can be skipped if defining overrides (InputConfig instance) from scratch without relying on anything from .conf.
    rb_cs.load_config_apply_overrides()

    forcing_config_dict = copy.deepcopy(rb_cs.input_configs["Forcing"])
    cs_overrides_dict = {
        "forcing_configuration": "short_range",
        "cold_start_datetime": DT_START_COLDSTART.strftime(DEFAULT_DATETIME_FORMAT),
        "cycle_datetime": DT_END_COLDSTART.strftime(DEFAULT_DATETIME_FORMAT),
    }
    forcing_config_dict.update(cs_overrides_dict)
    config_model = InputConfig(Forcing=ForcingConfig(**forcing_config_dict))
    print(f"Building coldstart realization: {config_model}")
    rb_cs.config_overrides = config_model
    rb_cs.build_fcst_realization()
    print(f"Wrote: {rb_cs.realization_file}")
    return rb_cs


def coldstart__build_and_run(state_manager: StateManager_Pseudo) -> None:
    """Build 1 coldstart realization and run it."""
    rb_cs = build_coldstart_realization()
    print(f"Running coldstart realization: {rb_cs.input_configs_class.Forcing}")
    run_fcst(valid_yaml=FORECAST_VALID_YAML, real_path=str(rb_cs.realization_file))
    state_manager.add_saved_state(
        SavedState_Pseudo(
            dt=datetime.strptime(rb_cs.input_configs_class.Forcing.cycle_datetime, DEFAULT_DATETIME_FORMAT),
            realization_file=rb_cs.realization_file,
        )
    )


def forecasts__build_and_run(
    test_manager: TestsManager,
    state_manager: StateManager_Pseudo,
    do_all_forcing_configs: bool,
    quit_forecast_after_forcing_running: bool,
    quit_forecast_after_duration: float | None,
) -> None:
    """
    Using ForecastTest, build and execute a list of forecast realizations.
    test_manager is modified in-place, so some test results may be available if this function is interrupted.
    """

    for config_overrides in get_test_configs__forecast(do_all_forcing_configs):
        fc = config_overrides.Forcing.forcing_configuration
        rb_kwargs = {
            # "input_path": FORECAST_CONFIG_FILE,
            "valid_yaml": FORECAST_VALID_YAML,
            "fcst_run_name": FORECAST_RUN_NAME,
            "config_overrides": config_overrides,
        }
        print(f"\n\n##########\n### {fc}: setting up test with rb_kwargs = {rb_kwargs}")

        t = ForecastTest(rb_kwargs=rb_kwargs, ngen_log=LogParser(path=TEST_NGEN_FORECAST_LOG_FILE))

        # Build the realization, trapping exceptions into class attrs
        print(f"### {fc}: building realization")
        t.make_realization_builder__build_realization(method="build_fcst_realization")

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
    do_coldstart: bool,
    do_all_forcing_configs: bool,
):
    if skip_forecast and do_all_forcing_configs:
        raise ValueError(
            f"Cannot use skip_forecast={skip_forecast} and do_all_forcing_configs={do_all_forcing_configs}"
        )
    utils_testing_setup.assert_paths__core(GAGE_ID)
    utils_testing_setup.assert_paths__raw_config(CALIB_CONFIG_FILE, FORECAST_CONFIG_FILE)

    # TODO pseudocode for now for states.
    state_manager = StateManager_Pseudo()
    tests_manager = TestsManager()

    ### NOTE this deletes the test output dir.
    ### If wanting to skip Calibration but still do CS and/or Forecast,
    ### then remove this line so that the test calibration results remain available.
    # utils_testing_setup.delete_test_output_dir(TEST_DIR_OUTPUT)

    if delete_scratch_and_mesh_first:
        utils_testing_setup.delete_files_to_force_esmf_and_netcdf_actions(GAGE_ID)

    if do_calibration:
        calibrations__build_and_run(tests_manager)

    if do_coldstart:
        # TODO implement test framework similar to forecast
        coldstart__build_and_run(state_manager)

    if not skip_forecast:
        forecasts__build_and_run(
            tests_manager,
            state_manager,
            do_all_forcing_configs,
            quit_forecast_after_forcing_running,
            quit_forecast_after_duration,
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
        help=f"Skip building and running forecasts. Incompatible with --do_all_forcing_configs.",
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
        "--do_coldstart",
        action="store_true",
        help="Build and run coldstart before forecasts",
    )
    parser.add_argument(
        "--do_all_forcing_configs",
        action="store_true",
        help=f"Run all forcing configurations rather than the default shorter default list. Default list: {FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT}. Incompatible with --skip_forecast.",
    )
    args = parser.parse_args()
    print(f"args: {args}")
    main(**vars(args))
