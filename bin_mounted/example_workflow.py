import functools
import os
import shutil
import subprocess

from mswm.build_inputs import RealizationBuilder
from nwm_fcst_mgr.forecast import run_fcst

print = functools.partial(print, flush=True)


FCST_RUN_NAME = "fcst_run1"
TEST_FORMULATION_SUFFIX = "bmi"
# TEST_FORMULATION_SUFFIX = "csv"

TEST_DIR_BASE = f"/ngwpc/run_ngen/kge_dds/test_{TEST_FORMULATION_SUFFIX}/01123000"
TEST_DIR_INPUT = f"{TEST_DIR_BASE}/Input"
TEST_DIR_OUTPUT = f"{TEST_DIR_BASE}/Output"

### Read by build_calib_realization()
CALIB_CONFIG_CONFIG = f"/ngwpc/run_ngen/cold_start_workflow/input_calibration_{TEST_FORMULATION_SUFFIX}.config"

### Written by build_calib_realization(), read by calibration.py
# CALIB_CONFIG_YAML = f"{TEST_DIR_INPUT}/01123000_config_calib.yaml"

### Read by build_fcst_realization() for CS and for Forecast
FORECAST_CONFIG_CONFIG = "/ngwpc/run_ngen/cold_start_workflow/input_forecast.config"
FORECAST_CONFIG_YAML = f"{TEST_DIR_OUTPUT}/Validation_Run/01123000_config_valid_best.yaml"

### Written by build_fcst_realization() for Forecast, read by run_fcst()
# REALIZATION_BMI_FORECAST_JSON = (
#     f"{TEST_DIR_OUTPUT}/Forecast_Run/{FCST_RUN_NAME}/01123000_realization_config_bmi_fcst.json"
# )

### Written by build_fcst_realization() for CS, read by run_fcst()
# REALIZATION_BMI_COLDSTART_JSON = (
#     f"{TEST_DIR_OUTPUT}/Cold_Start_Run/{FCST_RUN_NAME}/01123000_realization_config_bmi_cold_start.json"
# )


REALIZATION_KWARGS__COLDSTART_AND_FORECAST = {
    "input_path": FORECAST_CONFIG_CONFIG,
    "valid_yaml": FORECAST_CONFIG_YAML,
    "fcst_run_name": FCST_RUN_NAME,
}


def print_with_newlines(s: str) -> None:
    print(f"\n{os.path.basename(__file__)}: {s}\n")


def assert_paths() -> None:
    for path in [
        f"{TEST_DIR_INPUT}/ngen",
        f"{TEST_DIR_INPUT}/gauge_01123000.gpkg",
        f"{TEST_DIR_OUTPUT}/Cold_Start_Run/{FCST_RUN_NAME}/01123000_realization_config_bmi_cold_start.json",
        f"{TEST_DIR_OUTPUT}/Forecast_Run/{FCST_RUN_NAME}/01123000_realization_config_bmi_fcst.json",
        "/s3/ngwpc-hydrofabric/2.2/CONUS/01123000/GEOPACKAGE/USGS/2025_Mar_14_21_14_37/gauge_01123000.gpkg",
        # "/ngencerf/data/forecast_work",
        "/ngen-app",
        "/ngen-app/data",
        "/ngen-app/ngen/cmake_build/ngen",
        "/ngen-app/ngen/extern/sloth/cmake_build/libslothmodel.so",
        "/ngen-app/ngen/extern/cfe/cmake_build/libcfebmi.so",
        "/ngen-app/ngen/extern/LASAM/cmake_build/liblasambmi.so",
        "/ngen-app/ngen/extern/noah-owp-modular/cmake_build/libsurfacebmi.so",
        "/ngen-app/ngen/extern/evapotranspiration/evapotranspiration/cmake_build/libpetbmi.so",
        "/ngen-app/ngen/extern/sac-sma/cmake_build/libsacbmi.so",
        "/ngen-app/ngen/extern/SoilFreezeThaw/cmake_build/libsftbmi.so",
        # "/ngen-appngen/extern/SoilMoistureProfiles/cmake_build/libsmpbmi.so",
        "/ngen-app/ngen/extern/SoilMoistureProfiles/cmake_build/libsmpbmi.so",
        "/ngen-app/ngen/extern/snow17/cmake_build/libsnow17bmi.so",
        "/ngen-app/ngen/extern/topmodel/cmake_build/libtopmodelbmi.so",
        "/ngen-app/ngen/extern/ueb-bmi/cmake_build/src/libbmiuebcxx.so",
    ]:
        if not os.path.exists(path):
            raise FileNotFoundError(path)


def calibration__build_and_run() -> None:
    assert os.path.exists(CALIB_CONFIG_CONFIG)
    print(f"Deleting if exists: {TEST_DIR_OUTPUT}")
    try:
        shutil.rmtree(TEST_DIR_OUTPUT)
    except (FileNotFoundError, NotADirectoryError):
        pass
    print_with_newlines("Building calibration realization")
    rb_calib = RealizationBuilder(CALIB_CONFIG_CONFIG)
    rb_calib.build_calib_realization()
    # assert rb_calib.calib_config_file == CALIB_CONFIG_YAML
    assert os.path.exists(rb_calib.calib_config_file)

    print_with_newlines("Running calibration")
    cmd = [
        "python",
        "/ngen-app/bin/calibration.py",
        str(rb_calib.calib_config_file),
    ]
    print_with_newlines(f"Running command args: {cmd}")
    subprocess.check_call(cmd)


def coldstart__build() -> RealizationBuilder:
    print_with_newlines("Building coldstart realization")
    rb_cs = RealizationBuilder(**REALIZATION_KWARGS__COLDSTART_AND_FORECAST, use_cold_start=True)
    rb_cs.build_fcst_realization()
    # assert str(rb_cs.realization_file) == str(REALIZATION_BMI_COLDSTART_JSON)
    return rb_cs


def coldstart__run(rb_cs: RealizationBuilder) -> None:
    print_with_newlines("Running coldstart")
    run_fcst(
        valid_yaml=FORECAST_CONFIG_YAML,
        real_path=str(rb_cs.realization_file),
    )


def forecast__build() -> RealizationBuilder:
    print_with_newlines("Building forecast realization")
    rb_fcst = RealizationBuilder(**REALIZATION_KWARGS__COLDSTART_AND_FORECAST, use_cold_start=False)
    rb_fcst.build_fcst_realization()
    # assert str(rb_fcst.realization_file) == str(REALIZATION_BMI_FORECAST_JSON)
    return rb_fcst


def forecast__run(rb_fcst: RealizationBuilder) -> None:
    print_with_newlines("Running forecast")
    run_fcst(
        valid_yaml=FORECAST_CONFIG_YAML,
        real_path=str(rb_fcst.realization_file),
    )


def delete_input_symlinks() -> None:
    """Temporary workaround, this might be unnecessary in some branches"""
    for symlink in [
        "/ngwpc/run_ngen/kge_dds/noah_cfes/01123000/Input/noah-owp-modular_input/GENPARM.TBL",
        "/ngwpc/run_ngen/kge_dds/noah_cfes/01123000/Input/noah-owp-modular_input/MPTABLE.TBL",
        "/ngwpc/run_ngen/kge_dds/noah_cfes/01123000/Input/noah-owp-modular_input/SOILPARM.TBL",
        "/ngwpc/run_ngen/kge_dds/noah_cfes/01123000/Input/libslothmodel.so",
        "/ngwpc/run_ngen/kge_dds/noah_cfes/01123000/Input/libsurfacebmi.so",
        "/ngwpc/run_ngen/kge_dds/noah_cfes/01123000/Input/libcfebmi.so",
        "/ngwpc/run_ngen/kge_dds/noah_cfes/01123000/Input/ngen",
    ]:
        if os.path.islink(symlink):
            print(f"Deleting: {symlink}")
            os.remove(symlink)


def main():
    assert os.path.exists(FORECAST_CONFIG_CONFIG)
    assert os.path.exists("/ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/")

    ### TODO temporary workaround, this may not be needed in some branches
    # delete_input_symlinks()

    calibration__build_and_run()
    # return

    rb_cs = coldstart__build()
    rb_fcst = forecast__build()

    ### TODO run_fcst() could assert these files exist before it calls ngen
    assert_paths()

    coldstart__run(rb_cs)
    forecast__run(rb_fcst)


if __name__ == "__main__":
    main()
