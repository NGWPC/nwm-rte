"""Misc utilities for testing setup and teardown, and assertions on test config paths."""

import os
import shutil

from ngen_rte import consts as c
from ngen_rte.configs import RTETestConfig
from ngen_rte.logger import initialize_logger

LOG = initialize_logger()


def delete_test_output_dir(cfg: RTETestConfig) -> None:
    """Delete the test outputs directory"""
    for _, _, test_paths in cfg.get_calib_permutations():
        LOG.info(f"Deleting if exists: {test_paths.dir_output}")
        try:
            shutil.rmtree(test_paths.dir_output)
        except (FileNotFoundError, NotADirectoryError):
            pass


def delete_forcing_raw_inputs() -> None:
    """Delete the forcing raw inputs directory (clear forcing data cache)"""
    dir_raw_input = c.DIR_FORCING_RAW_INPUT
    LOG.info(f"Listing: {c.DIR_FORCING_RAW_INPUT}")
    for bn in os.listdir(dir_raw_input):
        fp = os.path.join(dir_raw_input, bn)
        if os.path.isdir(fp):
            LOG.info(f"Deleting directory: {fp}")
            shutil.rmtree(fp)
        else:
            LOG.info(f"Deleting file: {fp}")
            os.remove(fp)


def delete_scratch_and_esmf_outputs(cfg: RTETestConfig) -> None:
    """Delete the scratch dir and ESMF mesh outputs."""
    dirs_to_delete = [f"{c.DEFAULT_MAIN_DIR}/data/scratch"]
    for d in dirs_to_delete:
        if os.path.exists(d):
            LOG.info(f"Deleting: {d}")
            shutil.rmtree(d)
        else:
            LOG.info(f"Did not exist: {d}")

    files_to_delete = [
        f"{c.DEFAULT_MAIN_DIR}/data/esmf_mesh/gauge_{cfg.gage_id}_ESMF_Mesh.nc",
        f"/ngen-app/data/esmf_mesh/gauge_{cfg.gage_id}_ESMF_Mesh.nc",
    ]
    for f in files_to_delete:
        if os.path.exists(f):
            LOG.info(f"Deleting: {f}")
            os.remove(f)
        else:
            LOG.info(f"Did not exist: {f}")


def assert_paths__core(cfg: RTETestConfig) -> None:
    """Assert that various paths exist"""
    file_paths = [
        c.NGEN_BIN__LINK,
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


def assert_paths__raw_config(cfg: RTETestConfig) -> None:
    """Assert that various paths exist"""
    for _, _, test_paths in cfg.get_calib_permutations():
        for fp in [
            test_paths.calib_config_file,
            test_paths.fcst_config_file,
        ]:
            if not os.path.isfile(fp):
                raise FileNotFoundError(fp)
