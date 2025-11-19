import copy
from datetime import datetime
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


def coldstart__build() -> RealizationBuilder:
    print("Building coldstart realization")
    assert_paths_common_input()
    rb_cs = RealizationBuilder(**REALIZATION_KWARGS__COLDSTART_AND_FORECAST, use_cold_start=True)
    rb_cs.build_fcst_realization()
    if not os.path.isfile(rb_cs.realization_file):
        raise FileNotFoundError(rb_cs.realization_file)
    return rb_cs


def coldstart__run(rb_cs: RealizationBuilder) -> None:
    print("Running coldstart")
    run_fcst(
        valid_yaml=FORECAST_CONFIG_YAML,
        real_path=str(rb_cs.realization_file),
    )
    shutil.copyfile(TEST_NGEN_LOG_FILE, TEST_NGEN_LOG_FILE + ".coldstart.log")


def forecast__build() -> RealizationBuilder:
    print("Building forecast realization")
    assert_paths_common_input()
    rb_fcst = RealizationBuilder(**REALIZATION_KWARGS__COLDSTART_AND_FORECAST, use_cold_start=False)
    rb_fcst.build_fcst_realization()
    if not os.path.isfile(rb_fcst.realization_file):
        raise FileNotFoundError(rb_fcst.realization_file)

    print(f"\n##### vvv Config at Start vvv: \n{pprint.pformat(rb_fcst.input_configs)}\n##### ^^^ Config at Start ^^^")

    # forecast_types = mswm_valid_configs  # Full list of supported types
    forecast_types = [
        "short_range",
        "standard_ana",
        "medium_range_blend",
    ]

    cycle_datetimes = [
        datetime(year=2025, month=9, day=17, hour=0, minute=0, second=0),
        datetime(year=2025, month=9, day=18, hour=0, minute=0, second=0),
        datetime(year=2025, month=9, day=19, hour=0, minute=0, second=0),
    ]

    for fct in forecast_types:
        for cdt in cycle_datetimes:
            forcing_config = copy.deepcopy(rb_fcst.input_configs["Forcing"])
            forcing_config["forcing_configuration"] = fct
            forcing_config["cycle_datetime"] = cdt.strftime(mswm_settings.DEFAULT_DATETIME_FORMAT)

            rb_fcst.config_overrides = InputConfig(Forcing=ForcingConfig(**forcing_config))
            rb_fcst.build_fcst_realization()

            print(f"Config w/ overrides: forcing={fct}, cycle_datetime={cdt}: {pprint.pformat(rb_fcst.input_configs)}")

    print(f"rb_fcst.realization_file = {rb_fcst.realization_file}")
    if not os.path.isfile(rb_fcst.realization_file):
        raise FileNotFoundError(rb_fcst.realization_file)

    return rb_fcst


def forecast__run(rb_fcst: RealizationBuilder) -> None:
    print("Running forecast")
    run_fcst(
        valid_yaml=FORECAST_CONFIG_YAML,
        real_path=str(rb_fcst.realization_file),
    )
    shutil.copyfile(TEST_NGEN_LOG_FILE, TEST_NGEN_LOG_FILE + ".forecast.log")


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


def main():
    assert_paths__core()
    assert_paths__raw_config()

    ### NOTE this deletes the test output dir.
    ### If wanting to skip Calibration but still do CS and/or Forecast,
    ### then remove this line so that the test calibration results remain available.
    # delete_test_output_dir()

    delete_files_to_force_esmf_and_netcdf_actions()
    calibration__build_and_run()

    rb_cs = coldstart__build()
    rb_fcst = forecast__build()

    delete_files_to_force_esmf_and_netcdf_actions()
    coldstart__run(rb_cs)
    forecast__run(rb_fcst)


if __name__ == "__main__":
    main()
