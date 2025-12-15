import os
import shutil

from execution_tests import TestPaths, DIR_FORCING_RAW_INPUT


def delete_test_output_dir(test_paths: TestPaths) -> None:
    print(f"Deleting if exists: {test_paths.dir_output}")
    try:
        shutil.rmtree(test_paths.dir_output)
    except (FileNotFoundError, NotADirectoryError):
        pass


def delete_forcing_raw_inputs() -> None:
    dir_raw_input = DIR_FORCING_RAW_INPUT
    print(f"Listing: {DIR_FORCING_RAW_INPUT}")
    for bn in os.listdir(dir_raw_input):
        fp = os.path.join(dir_raw_input, bn)
        if os.path.isdir(fp):
            print(f"Deleting directory: {fp}")
            shutil.rmtree(fp)
        else:
            print(f"Deleting file: {fp}")
            os.remove(fp)


def delete_scratch_and_esmf_outputs(test_paths: TestPaths) -> None:
    dirs_to_delete = ["/ngwpc/run_ngen/data/scratch/NWM"]
    for d in dirs_to_delete:
        if os.path.exists(d):
            print(f"Deleting: {d}")
            shutil.rmtree(d)
        else:
            print(f"Did not exist: {d}")

    files_to_delete = [
        f"/ngwpc/run_ngen/data/esmf_mesh/gauge_{test_paths.gage_id}_ESMF_Mesh.nc",
        f"/ngen-app/data/esmf_mesh/gauge_{test_paths.gage_id}_ESMF_Mesh.nc",
    ]
    for f in files_to_delete:
        if os.path.exists(f):
            print(f"Deleting: {f}")
            os.remove(f)
        else:
            print(f"Did not exist: {f}")


def assert_paths__core(test_paths: TestPaths) -> None:
    file_paths = [
        f"/s3/ngwpc-hydrofabric/2.2/CONUS/{test_paths.gage_id}/GEOPACKAGE/USGS/{test_paths.gage_vintage}/gauge_{test_paths.gage_id}.gpkg",
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


def assert_paths__raw_config(test_paths: TestPaths) -> None:
    for fp in [
        test_paths.calib_config_file,
        test_paths.fcst_config_file,
    ]:
        if not os.path.isfile(fp):
            raise FileNotFoundError(fp)
