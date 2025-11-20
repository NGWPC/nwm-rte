import copy
from dataclasses import dataclass
from datetime import datetime, timedelta
import functools
import os
import pprint
import shutil
import subprocess

from mswm.build_inputs import RealizationBuilder
from mswm.utils.input_configuration import (
    InputConfig,
    ForcingConfig,
    valid_configs as mswm_valid_configs,
)
from mswm.utils import settings as mswm_settings

from nwm_fcst_mgr.forecast import run_fcst

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

### Read by build_calib_realization()
CALIB_CONFIG_CONFIG = f"/ngwpc/run_ngen/cold_start_workflow/input_calibration_{TEST_FORMULATION_SUFFIX}.config"
# CALIB_CONFIG_CONFIG = f"/ngwpc/run_ngen/cold_start_workflow/input_calibration_{TEST_FORMULATION_SUFFIX}_short.config"

### Read by build_fcst_realization() for CS and for Forecast
FORECAST_CONFIG_CONFIG = "/ngwpc/run_ngen/cold_start_workflow/input_forecast.config"
FORECAST_CONFIG_YAML = f"{TEST_DIR_OUTPUT}/Validation_Run/{GAGE_ID}_config_valid_best.yaml"


REALIZATION_KWARGS__COLDSTART_AND_FORECAST = {
    "input_path": FORECAST_CONFIG_CONFIG,
    "valid_yaml": FORECAST_CONFIG_YAML,
    "fcst_run_name": FCST_RUN_NAME,
}

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
        cycle_datetime=FORECAST_INITIAL_CYCLE_DATETIME.strftime(mswm_settings.DEFAULT_DATETIME_FORMAT),
        cold_start_datetime=None,
    )
)


FORECAST_TYPE_2_DELTA_HOURS = {
    # "aorc": 1,  # AttributeError: 'RealizationBuilder' object has no attribute 'time_period'
    # "nwm": 1,  # AttributeError: 'RealizationBuilder' object has no attribute 'time_period'
    # "standard_ana": 1,  # good default
    # "standard_ana_alaska": 1,
    # "standard_ana_hawaii": 1,
    # "standard_ana_puertorico": 1,
    # "extended_ana": 24,
    # "extended_ana_alaska": 24,
    "short_range": 1,  # good default
    # "short_range_alaska": 1,
    # "short_range_hawaii": 1,  # FileNotFoundError: Forcing template file does not exist: /ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/short_range_hawaii_config.yml
    # "short_range_puertorico": 1,
    # "short_range_extended_alaska": 6,
    # "medium_range_blend": 6,  # good default
    # "medium_range_blend_alaska": 6,
    # "long_range_mem1": 6,
    # "long_range_mem2": 6,
    # "long_range_mem3": 6,
    # "long_range_mem4": 6,
}


@dataclass
class SavedStartState_PseudoCode:
    """Pseudocode"""

    forecast_type: str
    cycle_datetime: datetime
    realization_file: str


def assert_paths__core() -> None:
    file_paths = [
        f"/s3/ngwpc-hydrofabric/2.2/CONUS/{GAGE_ID}/GEOPACKAGE/USGS/2025_Mar_14_21_14_37/gauge_{GAGE_ID}.gpkg",
        "/ngen-app/ngen/cmake_build/ngen",
        "/ngen-app/ngen/extern/sloth/cmake_build/libslothmodel.so",
        "/ngen-app/ngen/extern/cfe/cmake_build/libcfebmi.so",
        "/ngen-app/ngen/extern/LASAM/cmake_build/liblasambmi.so",
        "/ngen-app/ngen/extern/noah-owp-modular/cmake_build/libsurfacebmi.so",
        "/ngen-app/ngen/extern/evapotranspiration/evapotranspiration/cmake_build/libpetbmi.so",
        "/ngen-app/ngen/extern/sac-sma/cmake_build/libsacbmi.so",
        "/ngen-app/ngen/extern/SoilFreezeThaw/cmake_build/libsftbmi.so",
        "/ngen-app/ngen/extern/SoilMoistureProfiles/cmake_build/libsmpbmi.so",
        "/ngen-app/ngen/extern/snow17/cmake_build/libsnow17bmi.so",
        "/ngen-app/ngen/extern/topmodel/cmake_build/libtopmodelbmi.so",
        "/ngen-app/ngen/extern/ueb-bmi/cmake_build/src/libbmiuebcxx.so",
    ]
    dir_paths = [
        "/ngen-app",
        "/ngen-app/data",
        "/ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates",
    ]
    for fp in file_paths:
        if not os.path.isfile(fp):
            raise FileNotFoundError(fp)
    for dp in dir_paths:
        if not os.path.isdir(dp):
            raise NotADirectoryError(fp)


def assert_paths__raw_config():
    for fp in [
        CALIB_CONFIG_CONFIG,
        FORECAST_CONFIG_CONFIG,
    ]:
        if not os.path.isfile(fp):
            raise FileNotFoundError(fp)


def assert_paths_common_input():
    for fp in [
        f"{TEST_DIR_INPUT}/ngen",
        f"{TEST_DIR_INPUT}/gauge_{GAGE_ID}.gpkg",
    ]:
        if not os.path.isfile(fp):
            raise FileNotFoundError(fp)


def calibration__build_and_run() -> None:
    print("Building calibration realization")
    rb_calib = RealizationBuilder(CALIB_CONFIG_CONFIG)
    rb_calib.build_calib_realization()
    assert_paths_common_input()
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
    shutil.copyfile(TEST_NGEN_LOG_FILE, TEST_NGEN_LOG_FILE + ".calib.log")


def delete_test_output_dir():
    print(f"Deleting if exists: {TEST_DIR_OUTPUT}")
    try:
        shutil.rmtree(TEST_DIR_OUTPUT)
    except (FileNotFoundError, NotADirectoryError):
        pass


def delete_files_to_force_esmf_and_netcdf_actions():
    dirs_to_delete = ["/ngwpc/run_ngen/data/scratch/NWM"]
    for d in dirs_to_delete:
        if os.path.exists(d):
            print(f"Deleting: {d}")
            shutil.rmtree(d)
        else:
            print(f"Did not exist: {d}")

    files_to_delete = [
        f"/ngwpc/run_ngen/data/esmf_mesh/gauge_{GAGE_ID}_ESMF_Mesh.nc",
        f"/ngen-app/data/esmf_mesh/gauge_{GAGE_ID}_ESMF_Mesh.nc",
    ]
    for f in files_to_delete:
        if os.path.exists(f):
            print(f"Deleting: {f}")
            os.remove(f)
        else:
            print(f"Did not exist: {f}")


def build_coldstart_realization():
    rb_cs = RealizationBuilder(**REALIZATION_KWARGS__COLDSTART_AND_FORECAST, use_cold_start=True)
    # This can be called before the overrides (InputConfig instance) is defined, to load the .conf file first without overrides.
    # Then overrides can be idiomatically defined by copying the valid config and replacing individual keys.
    # This can be skipped if defining overrides (InputConfig instance) from scratch without relying on anything from .conf.
    rb_cs.load_config_apply_overrides()

    forcing_config = copy.deepcopy(rb_cs.input_configs["Forcing"])
    cs_overrides_dict = {
        "forcing_configuration": "short_range",
        "cold_start_datetime": COLDSTART_START.strftime(mswm_settings.DEFAULT_DATETIME_FORMAT),
        "cycle_datetime": COLDSTART_END.strftime(mswm_settings.DEFAULT_DATETIME_FORMAT),
    }
    forcing_config.update(cs_overrides_dict)
    print(f"Building coldstart realization: {forcing_config}")
    rb_cs.config_overrides = InputConfig(Forcing=ForcingConfig(**forcing_config))
    rb_cs.build_fcst_realization()
    print(f"Wrote: {rb_cs.realization_file}")
    return rb_cs


def generate_forecasts():
    for i in range(FORECAST_ROUNDS):
        if i == 0:
            # TODO for first run, how to use the coldstart results from `saved_start_states_pseudocode`?
            forecast_type_2_delta_hours = {fct: 0 for fct in FORECAST_TYPE_2_DELTA_HOURS}
        else:
            # TODO for subsequent runs, how to use the ANA results from `saved_start_states_pseudocode`?
            forecast_type_2_delta_hours = FORECAST_TYPE_2_DELTA_HOURS

        rb_fcst = RealizationBuilder(**REALIZATION_KWARGS__COLDSTART_AND_FORECAST, use_cold_start=False)
        rb_fcst.load_config_apply_overrides()
        forcing_config = copy.deepcopy(rb_fcst.input_configs["Forcing"])

        for fct, delta_hours in forecast_type_2_delta_hours.items():
            cycle_datetime = FORECAST_INITIAL_CYCLE_DATETIME + timedelta(hours=i * delta_hours)

            fcst_overrides_dict = {
                "forcing_configuration": fct,
                "cold_start_datetime": None,
                "cycle_datetime": cycle_datetime.strftime(mswm_settings.DEFAULT_DATETIME_FORMAT),
            }

            forcing_config.update(fcst_overrides_dict)
            print(f"\nRound {i} {fct}: building forecast realization: {forcing_config}")
            rb_fcst.config_overrides = InputConfig(Forcing=ForcingConfig(**forcing_config))
            rb_fcst.build_fcst_realization()
            print(f"Wrote: {rb_fcst.realization_file}")
            yield rb_fcst


def main():
    assert_paths__core()
    assert_paths__raw_config()
    assert_paths_common_input()

    ### NOTE this deletes the test output dir.
    ### If wanting to skip Calibration but still do CS and/or Forecast,
    ### then remove this line so that the test calibration results remain available.
    # delete_test_output_dir()

    # delete_files_to_force_esmf_and_netcdf_actions()
    calibration__build_and_run()

    # TODO pseudocode for now for states.
    saved_start_states_pseudocode: list[SavedStartState_PseudoCode] = []

    rb_cs = build_coldstart_realization()
    print(f'Running coldstart realization: {rb_cs.input_configs["Forcing"]}')
    run_fcst(valid_yaml=FORECAST_CONFIG_YAML, real_path=str(rb_cs.realization_file))
    saved_start_states_pseudocode.append(
        SavedStartState_PseudoCode(
            forecast_type=rb_cs.input_configs["Forcing"]["forcing_configuration"],
            cycle_datetime=COLDSTART_END,
            realization_file=rb_cs.realization_file,
        )
    )

    for rb_fcst in generate_forecasts():
        print(f'Running forecast realization: {rb_fcst.input_configs["Forcing"]}')
        run_fcst(valid_yaml=FORECAST_CONFIG_YAML, real_path=str(rb_fcst.realization_file))
        if rb_fcst.input_configs["Forcing"]["forcing_configuration"] == "standard_ana":
            sss = SavedStartState_PseudoCode(
                forecast_type=rb_fcst.input_configs["Forcing"]["forcing_configuration"],
                cycle_datetime=rb_fcst.input_configs["Forcing"]["cycle_datetime"].strptime(
                    mswm_settings.DEFAULT_DATETIME_FORMAT
                ),
                realization_file=rb_fcst.realization_file,
            )
            saved_start_states_pseudocode.append(sss)


if __name__ == "__main__":
    main()
