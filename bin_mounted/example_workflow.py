import argparse
import copy
from dataclasses import dataclass
from datetime import datetime, timedelta
import functools
import os
import pprint
import shutil
import subprocess
import time
import typing

from mswm.build_inputs import RealizationBuilder
from mswm.utils.input_configuration import (
    InputConfig,
    GeneralConfig,
    ForcingConfig,
    valid_configs as mswm_valid_configs,
)
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

from nwm_fcst_mgr.forecast import run_fcst, ForecastExecutionManager, RunStatus
from nwm_fcst_mgr.exceptions import NgenIntentionallyStoppedError

import utils_testing_setup
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

REALIZATION_KWARGS__FORECAST = {
    # "input_path": FORECAST_CONFIG_CONFIG,  # From disk
    "valid_yaml": FORECAST_CONFIG_YAML,
    "fcst_run_name": FCST_RUN_NAME,
    "config_overrides": DEFAULT_FORECAST_CONFIG,  # From memory
}

FORECAST_TYPE_2_DELTA_HOURS = {
    # "aorc": 1,  # AttributeError: 'RealizationBuilder' object has no attribute 'time_period'
    # "nwm": 1,  # AttributeError: 'RealizationBuilder' object has no attribute 'time_period'
    "standard_ana": 1,
    "standard_ana_alaska": 1,
    "standard_ana_hawaii": 1,
    "standard_ana_puertorico": 1,
    "extended_ana": 24,
    "extended_ana_alaska": 24,
    "short_range": 1,
    "short_range_alaska": 1,
    # "short_range_hawaii": 1,  # FileNotFoundError: Forcing template file does not exist: /ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/short_range_hawaii_config.yml
    "short_range_puertorico": 1,
    "short_range_extended_alaska": 6,
    "medium_range_blend": 6,
    "medium_range_blend_alaska": 6,
    "long_range_mem1": 6,
    "long_range_mem2": 6,
    "long_range_mem3": 6,
    "long_range_mem4": 6,
}
FCST_TYPES__DEFAULT = ["short_range", "standard_ana", "medium_range_blend"]
FCST_TYPES__ALL = list(FORECAST_TYPE_2_DELTA_HOURS)


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


def generate_forecasts(fcst_types: list[str]) -> typing.Generator[RealizationBuilder, None, None]:
    """Generator. Build a series of forecast realizations,
    including multiple forcing configurations defined by `fcst_types` and multiple cycle datetimes defined by `FORECAST_ROUNDS`.
    """
    for i in range(FORECAST_ROUNDS):
        # TODO apply coldstart state to first round, apply ANA state to subsequent rounds
        rb_fcst = RealizationBuilder(**REALIZATION_KWARGS__FORECAST, use_cold_start=False)
        rb_fcst.load_config_apply_overrides()
        forcing_config_dict = copy.deepcopy(rb_fcst.input_configs["Forcing"])

        for fct in fcst_types:
            delta_hours = FORECAST_TYPE_2_DELTA_HOURS[fct]
            cycle_datetime = FORECAST_INITIAL_CYCLE_DATETIME + timedelta(hours=i * delta_hours)

            fcst_overrides_dict = {
                "forcing_configuration": fct,
                "cold_start_datetime": None,
                "cycle_datetime": cycle_datetime.strftime(DEFAULT_DATETIME_FORMAT),
            }

            forcing_config_dict.update(fcst_overrides_dict)
            config_model = InputConfig(Forcing=ForcingConfig(**forcing_config_dict))
            print(f"\nRound {i+1} {fct}: building forecast realization: {config_model}")
            rb_fcst.config_overrides = config_model
            rb_fcst.build_fcst_realization()
            print(f"Wrote: {rb_fcst.realization_file}")
            yield rb_fcst


def infer_from_log__forcing_is_running(ngen_log_path: str) -> bool:
    """Read the log file and look for sentinel messages.
    If they exist, assume the forcing is running successfully and return True."""
    if os.path.exists(ngen_log_path):
        print(f"Reading: {ngen_log_path}")
        with open(ngen_log_path, "r") as f:
            log_content = f.read()
    else:
        print(f"Does not exist yet: {ngen_log_path}")
        return False
    if (
        log_content.lower().count("processing forecast cycle") > 1
        and log_content.lower().count("writing output forcing file for timestamp") > 0
    ):
        return True
    else:
        return False


def wait_for_forcing_is_running(fem: ForecastExecutionManager, start: float):
    poll_freq_seconds = 10
    print(f"Polling ngen process every {poll_freq_seconds} seconds...")
    while True:
        duration_sec = time.perf_counter() - start
        fem.poll_ngen_flush_log()
        if duration_sec > 10 and infer_from_log__forcing_is_running(TEST_NGEN_FORECAST_LOG_FILE):
            print(f"After {duration_sec:.1f} seconds, ngen log indicates forcing is running successfully")
            break
        if fem.status == RunStatus.EXECUTION_SUCCESS:
            print(f"After {duration_sec:.1f} seconds, ngen finished running")
            break
        print(f"ngen has been running for {duration_sec:.1f} seconds...")
        # fem.schedule_ngen_stoppage()
        time.sleep(poll_freq_seconds)


def forecasts__build_and_run(
    state_manager: StateManager_Pseudo, fcst_types: list[str], quit_forecast_after_forcing_running: bool
) -> None:
    """Build a series of forecast realizations and run them,
    including multiple forcing configurations defined by `fcst_types` and multiple cycle datetimes defined by `FORECAST_ROUNDS`.
    """
    for rb_fcst in generate_forecasts(fcst_types):
        print(f"Running forecast realization: {rb_fcst.input_configs_class.Forcing}")
        if quit_forecast_after_forcing_running:
            try:
                with ForecastExecutionManager(
                    valid_yaml=FORECAST_CONFIG_YAML, real_path=str(rb_fcst.realization_file)
                ) as fem:
                    fem.preprocess()
                    fem.execute(wait=False)  # When wait=false,
                    wait_for_forcing_is_running(fem, start=time.perf_counter())
            except NgenIntentionallyStoppedError:
                # Raised when stop flag is manually set, or when context manager ends before ngen finishes.
                # The latter is happening intentionally here.
                pass
        else:
            run_fcst(valid_yaml=FORECAST_CONFIG_YAML, real_path=str(rb_fcst.realization_file))

        if rb_fcst.input_configs_class.Forcing.forcing_configuration == "standard_ana":
            state_manager.add_saved_state(
                SavedState_Pseudo(
                    dt=datetime.strptime(rb_fcst.input_configs_class.Forcing.cycle_datetime, DEFAULT_DATETIME_FORMAT),
                    realization_file=rb_fcst.realization_file,
                )
            )
        # return


def main(
    delete_scratch_and_mesh_first: bool,
    skip_forecast: bool,
    quit_forecast_after_forcing_running: bool,
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
        calibration__build_and_run()

    if do_coldstart:
        coldstart__build_and_run(state_manager)

    if not skip_forecast:
        fcst_types = FCST_TYPES__ALL if do_all_forcing_configs else FCST_TYPES__DEFAULT
        forecasts__build_and_run(state_manager, fcst_types, quit_forecast_after_forcing_running)


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
        help="Instead of waiting for the forecast to finish, quit after the ngen log file indicates that forcing is running successfully.",
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
        help=f"Run all forcing configurations rather than the default shorter default list. Default list: {FCST_TYPES__DEFAULT}. Incompatible with --skip_forecast.",
    )
    args = parser.parse_args()
    print(f"args: {args}")
    main(**vars(args))
