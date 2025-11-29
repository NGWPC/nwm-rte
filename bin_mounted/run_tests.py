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
    valid_configs as mswm_valid_configs,
)
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

from nwm_fcst_mgr.forecast import run_fcst

import utils_testing_setup
from execution_tests import (
    ForecastTestManager,
    get_test_configs__forecast,
    FORCING_CONFIGURATION_TYPES__DEFAULT,
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


GAGE_ID = "01123000"
FCST_RUN_NAME = "fcst_run1"
TEST_FORMULATION_SUFFIX = "bmi"
# TEST_FORMULATION_SUFFIX = "csv"

TEST_DIR_BASE = f"/ngwpc/run_ngen/kge_dds/test_{TEST_FORMULATION_SUFFIX}/{GAGE_ID}"
TEST_DIR_INPUT = f"{TEST_DIR_BASE}/Input"
TEST_DIR_OUTPUT = f"{TEST_DIR_BASE}/Output"
TEST_NGEN_LOG_FILE = f"{TEST_DIR_BASE}/logs/ngen.log"
TEST_NGEN_FORECAST_LOG_FILE = f"{TEST_DIR_OUTPUT}/Forecast_Run/{FCST_RUN_NAME}/logs/ngen.log"

### Read by build_calib_realization()
CALIB_CONFIG_CONFIG = f"/ngwpc/run_ngen/cold_start_workflow/input_calibration_{TEST_FORMULATION_SUFFIX}.config"
# CALIB_CONFIG_CONFIG = f"/ngwpc/run_ngen/cold_start_workflow/input_calibration_{TEST_FORMULATION_SUFFIX}_short.config"

### Read by build_fcst_realization() for CS and for Forecast
FORECAST_CONFIG_CONFIG = "/ngwpc/run_ngen/cold_start_workflow/input_forecast.config"
FORECAST_CONFIG_YAML = f"{TEST_DIR_OUTPUT}/Validation_Run/{GAGE_ID}_config_valid_best.yaml"


FORECAST_ROUNDS = 1
COLDSTART_START = datetime(year=2025, month=9, day=15, hour=0, minute=0, second=0)
COLDSTART_END = COLDSTART_START + timedelta(days=2)
FORECAST_INITIAL_CYCLE_DATETIME = COLDSTART_END


DEFAULT_FORECAST_CONFIG = InputConfig(
    Forcing=ForcingConfig(
        forcing_provider=TEST_FORMULATION_SUFFIX,
        forcing_dir=None,
        forcing_template_dir="/ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/",
        root_dir="/ngen-app/data",
        forcing_configuration="short_range",
        cycle_datetime=FORECAST_INITIAL_CYCLE_DATETIME.strftime(DEFAULT_DATETIME_FORMAT),
        cold_start_datetime=None,
    )
)

REALIZATION_KWARGS__COLDSTART = {
    "input_path": FORECAST_CONFIG_CONFIG,  # From disk
    "valid_yaml": FORECAST_CONFIG_YAML,
    "fcst_run_name": FCST_RUN_NAME,
}


def calibration__build_and_run() -> None:
    """Build 1 calibration realization and run it."""
    rb_calib = RealizationBuilder(CALIB_CONFIG_CONFIG)
    rb_calib.load_config_apply_overrides()
    print(f"Building calibration realization: {rb_calib.input_configs_class}")
    rb_calib.build_calib_realization()
    if not os.path.isfile(rb_calib.calib_config_file):
        raise FileNotFoundError(rb_calib.calib_config_file)
    print("Running calibration")
    cmd = [
        "python",
        "/ngen-app/bin/calibration.py",
        str(rb_calib.calib_config_file),
    ]
    print(f"Running command args: {cmd}")
    subprocess.check_call(cmd)


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
        "cold_start_datetime": COLDSTART_START.strftime(DEFAULT_DATETIME_FORMAT),
        "cycle_datetime": COLDSTART_END.strftime(DEFAULT_DATETIME_FORMAT),
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
    run_fcst(valid_yaml=FORECAST_CONFIG_YAML, real_path=str(rb_cs.realization_file))
    state_manager.add_saved_state(
        SavedState_Pseudo(
            dt=datetime.strptime(rb_cs.input_configs_class.Forcing.cycle_datetime, DEFAULT_DATETIME_FORMAT),
            realization_file=rb_cs.realization_file,
        )
    )


def forecasts__build_and_run(
    state_manager: StateManager_Pseudo,
    do_all_forcing_configs: bool,
    quit_forecast_after_forcing_running: bool,
    quit_forecast_after_duration: float | None,
) -> list[ForecastTestManager]:
    """
    Using ForecastTestManager, build and execute a list of forecast realizations.
    Return a list of instances of ForecastTestManager after attempting build + execute on each.
    """

    fcst_test_cases: list[ForecastTestManager] = []

    for config_overrides in get_test_configs__forecast(do_all_forcing_configs):
        fc = config_overrides.Forcing.forcing_configuration
        rb_kwargs = {
            # "input_path": FORECAST_CONFIG_CONFIG,
            "valid_yaml": FORECAST_CONFIG_YAML,
            "fcst_run_name": FCST_RUN_NAME,
            "config_overrides": config_overrides,
        }
        print(f"\n\n##########\n### {fc}: setting up test with rb_kwargs = {rb_kwargs}")
        t = ForecastTestManager(rb_kwargs=rb_kwargs, ngen_log_path=TEST_NGEN_FORECAST_LOG_FILE)
        fcst_test_cases.append(t)

        # Build the realization, trapping exceptions into class attrs
        print(f"### {fc}: building realization")
        t.make_realization_builder__build_realization()

        if t.test_realization_builder_passed:
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

    return fcst_test_cases


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
    utils_testing_setup.assert_paths__raw_config(CALIB_CONFIG_CONFIG, FORECAST_CONFIG_CONFIG)

    # TODO pseudocode for now for states.
    state_manager = StateManager_Pseudo()

    ### NOTE this deletes the test output dir.
    ### If wanting to skip Calibration but still do CS and/or Forecast,
    ### then remove this line so that the test calibration results remain available.
    # utils_testing_setup.delete_test_output_dir(TEST_DIR_OUTPUT)

    if delete_scratch_and_mesh_first:
        utils_testing_setup.delete_files_to_force_esmf_and_netcdf_actions(GAGE_ID)

    if do_calibration:
        # TODO implement test framework similar to forecast
        calibration__build_and_run()

    if do_coldstart:
        # TODO implement test framework similar to forecast
        coldstart__build_and_run(state_manager)

    if not skip_forecast:
        fcst_test_cases = forecasts__build_and_run(
            state_manager,
            do_all_forcing_configs,
            quit_forecast_after_forcing_running,
            quit_forecast_after_duration,
        )
        test_results_sums = {
            "builds_passed": sum(1 for t in fcst_test_cases if t.test_realization_builder_passed),
            "builds_failed": sum(1 for t in fcst_test_cases if not t.test_realization_builder_passed),
            "executions_passed": sum(1 for t in fcst_test_cases if t.test_forecast_execution_passed),
            "executions_failed": sum(1 for t in fcst_test_cases if not t.test_forecast_execution_passed),
        }
        test_results_file = os.path.join(os.path.dirname(__file__), "forecast_tests_results.json")
        msg = f"\n\n###### FORECAST TEST RESULTS ######\nWriting to: {test_results_file}\n{json.dumps(test_results_sums, indent=2)}"
        print(msg)
        with open(test_results_file, "w") as f:
            f.write(json.dumps(fcst_test_cases, indent=2, default=pydantic_encoder))
        if test_results_sums["builds_failed"] or test_results_sums["executions_failed"]:
            raise RuntimeError(test_results_sums)


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
        help=f"Run all forcing configurations rather than the default shorter default list. Default list: {FORCING_CONFIGURATION_TYPES__DEFAULT}. Incompatible with --skip_forecast.",
    )
    args = parser.parse_args()
    print(f"args: {args}")
    main(**vars(args))
