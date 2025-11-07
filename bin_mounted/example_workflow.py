import functools
import os
import shutil
import subprocess

from mswm.build_inputs import RealizationBuilder
from nwm_fcst_mgr.forecast import run_fcst

print = functools.partial(print, flush=True)

# import logging
# import sys
# logging.basicConfig(
#     level=logging.INFO,
#     handler=logging.StreamHandler(sys.stdout),
#     format="%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s",
# )


FCST_RUN_NAME = "fcst_run1"
TEST_FORMULATION_SUFFIX = "bmi"
# TEST_FORMULATION_SUFFIX = "csv"

TEST_DIR_BASE = f"/ngwpc/run_ngen/kge_dds/test_{TEST_FORMULATION_SUFFIX}/01123000"
TEST_DIR_INPUT = f"{TEST_DIR_BASE}/Input"
TEST_DIR_OUTPUT = f"{TEST_DIR_BASE}/Output"
TEST_NGEN_LOG_FILE = f"{TEST_DIR_BASE}/logs/ngen.log"

### Read by build_calib_realization()
CALIB_CONFIG_CONFIG = f"/ngwpc/run_ngen/cold_start_workflow/input_calibration_{TEST_FORMULATION_SUFFIX}.config"

### Read by build_fcst_realization() for CS and for Forecast
FORECAST_CONFIG_CONFIG = "/ngwpc/run_ngen/cold_start_workflow/input_forecast.config"
FORECAST_CONFIG_YAML = f"{TEST_DIR_OUTPUT}/Validation_Run/01123000_config_valid_best.yaml"


REALIZATION_KWARGS__COLDSTART_AND_FORECAST = {
    "input_path": FORECAST_CONFIG_CONFIG,
    "valid_yaml": FORECAST_CONFIG_YAML,
    "fcst_run_name": FCST_RUN_NAME,
}


def assert_paths__core() -> None:
    file_paths = [
        f"{TEST_DIR_INPUT}/ngen",
        f"{TEST_DIR_INPUT}/gauge_01123000.gpkg",
        "/s3/ngwpc-hydrofabric/2.2/CONUS/01123000/GEOPACKAGE/USGS/2025_Mar_14_21_14_37/gauge_01123000.gpkg",
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


def calibration__build_and_run() -> None:
    print("Building calibration realization")
    rb_calib = RealizationBuilder(CALIB_CONFIG_CONFIG)
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
    shutil.copyfile(TEST_NGEN_LOG_FILE, TEST_NGEN_LOG_FILE + ".calib.log")


def coldstart__build() -> RealizationBuilder:
    print("Building coldstart realization")
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
    rb_fcst = RealizationBuilder(**REALIZATION_KWARGS__COLDSTART_AND_FORECAST, use_cold_start=False)
    rb_fcst.build_fcst_realization()
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


def main():
    assert_paths__core()
    assert_paths__raw_config()

    # NOTE this deletes the test output dir.
    # If wanting to skip Calibration but still do CS and/or Forecast,
    # then remove this line so that the test calibration results remain available.
    delete_test_output_dir()
    calibration__build_and_run()

    rb_cs = coldstart__build()
    rb_fcst = forecast__build()

    coldstart__run(rb_cs)
    forecast__run(rb_fcst)


if __name__ == "__main__":
    main()
