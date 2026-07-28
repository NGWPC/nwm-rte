"""Constants"""

import getpass
import json
import os
from datetime import datetime, timedelta

from calib.strategy import (
    Algorithm as CalOptimizationAlgo,
)
from calib.strategy import (
    Objective as CalObjective,
)

PYTHON_VERSION_STRING = "3.12"
"""Python version string, e.g. "3.12". If this is changed here, it should also be changed in the build code in config.bashrc"""
CONTAINER_LOGS_DIR = "/ngen-app/logs_rte"

RUN_NAME_TIMESTAMP_SUFFIX_FORMAT = r"%Y%m%d-%H%M%S-%f"

FORCING_PROVIDER = "bmi"


### .config section [Forcing]
DEFAULT_FORECAST_RUN_NAME = "fcst_run1"
FORCING_TEMPLATE_DIR = f"/ngen-app/ngen-python/lib/python3.11/site-packages/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/"
"""Directory of forcing configuration template yaml files."""
FORCING_ROOT_DIR = "/ngen-app/data"
DIR_FORCING_RAW_INPUT = os.path.join(FORCING_ROOT_DIR, "raw_input")
DT_START_FORECAST = datetime(year=2025, month=9, day=15, hour=0, minute=0, second=0)
DT_START_COLDSTART = DT_START_FORECAST - timedelta(days=2)
DT_END_COLDSTART = DT_START_FORECAST


### .config section [General]
DEFAULT_GAGE_ID = "01123000"
DEFAULT_ENVIRONMENT = "test"

DEFAULT_MODEL_FORMULATION_ARGS = ("noah-owp-modular,cfe-s", False)
# DEFAULT_MODEL_FORMULATION_ARGS = ("snow-17,noah-owp-modular,smp,lasam,t-route", False)
# DEFAULT_MODEL_FORMULATION_ARGS = ("lstm", False)
"""Used to construct configs.ModelFormulation. 1st arg is csv str of models, 2nd arg is Boolean passed to ModulePropertiesConfig.cfe_aet_rootzone"""

DEFAULT_MAIN_DIR = "/ngwpc/run_ngen"


### .config section [Calibration]
CALIB_OBJECTIVE_FUNCTION = CalObjective.kge
CALIB_OPTIMIZATION_ALGO = CalOptimizationAlgo.dds
CALIB_PARAMETERS_DIR = f"{DEFAULT_MAIN_DIR}/data/calib_params_tab_delimited"
CALIB_ITER_START = 0
CALIB_ITER_COUNT = 2
CALIB_SAVE_PLOT_ITER_FREQ = 1
# Only needed for optimization algo PSO and GWO
CALIB_SWARM_SIZE = 3
# Only needed for optimization algo PSO
CALIB_PSO_C1 = 2
CALIB_PSO_C2 = 2
CALIB_PSO_W = 0.7
# Timing
CALIB_SIM_START_DEFAULT = datetime(
    year=2013, month=7, day=25, hour=0, minute=0, second=0
)
CALIB_SIM_DURATION_DEFAULT = timedelta(hours=47)
CALIB_EVAL_DELAYMENT_DEFAULT = timedelta(hours=0)  # Gets added
VALID_SIM_ADVANCEMENT_DEFAULT = timedelta(hours=0)  # Gets subtracted
VALID_EVAL_CURTAILMENT_DEFAULT = timedelta(hours=0)  # Gets subtracted

### .config section [DataFile]
MODULE_PARAMETER_FILES_DIR = f"/ngen-app/ngen-python/lib/python3.11/site-packages/mswm/module_parameter_files"
NGEN_DIR = "/ngen-app/ngen"
NWM_RETRO_STREAMFLOW_DIR = f"{DEFAULT_MAIN_DIR}/data/nwm_retrospective"


### .config section [Parallel]
DEFAULT_NPROCS = 1


### Test settings
TEST_RESULTS_FILE = os.path.join(
    os.path.dirname(__file__), "forecast_tests_results.json"
)

### Test Hydrofabric GPKG
TEST_HYDROFAB_FILE = (
    f"/ngen-app/bin/ngen_rte/tests/test_data/gauge_{DEFAULT_GAGE_ID}.gpkg"
)

### See this for full list of forcing configuration types: mswm.utils.input_configuration.mswm_valid_configs
FORECAST_FORCING_TYPES__TESTS = [
    "short_range",
    "standard_ana",
    "medium_range_blend",
]
# FORECAST_FORCING_TYPES__TESTS = ["short_range"]
FORECAST_FORCING_TYPES = [
    "standard_ana",
    "standard_ana_alaska",
    "standard_ana_hawaii",
    "standard_ana_puertorico",
    "extended_ana",
    "extended_ana_alaska",
    "short_range",
    "short_range_alaska",
    "short_range_hawaii",
    "short_range_puertorico",
    "short_range_extended_alaska",
    "medium_range_blend",
    "medium_range_blend_alaska",
    "long_range_mem1",
    "long_range_mem2",
    "long_range_mem3",
    "long_range_mem4",
]

CALIB_FORCING_TYPES = ["aorc", "nwm"]

ALL_FORCING_TYPES = FORECAST_FORCING_TYPES + CALIB_FORCING_TYPES + ["medium_range"]

GLOBAL_DOMAINS = [
    "CONUS",
    "Alaska",
    "Hawaii",
    "Puerto_Rico",
    "GL",  # Guam / Luta
]
"""The first value is the default"""

FORCING_STATIC_DIR_DEFAULT = "/ngen-app/data"

OUTPUT_FORMAT_DEFAULT = ["CSV"]

### This is where the ngen Dockerfile writes its binary executables
NGEN_BIN__TARGET = f"{NGEN_DIR}/cmake_build/ngen"
PARTITION_GENERATOR_BIN__TARGET = f"{NGEN_DIR}/cmake_build/partitionGenerator"
### This is where we create symlinks that point to the above paths
WCOSS_LOG_NAME = getpass.getuser()
WCOSS_NWM_VERS = "vX.Y.Z"
# Pattern from: https://www.nco.ncep.noaa.gov/idsb/implementation_standards/ImplementationStandards.v11.0.0.pdf
NGEN_EXE_DIR = (
    f"/lfs/h1/owp/nwm/noscrub/{WCOSS_LOG_NAME}/test/packages/nwm.{WCOSS_NWM_VERS}/exec"
)
NGEN_BIN__LINK = f"{NGEN_EXE_DIR}/ngen"
PARTITION_GENERATOR_BIN__LINK = f"{NGEN_EXE_DIR}/partitionGenerator"


### For construction of DataFileConfig
### NOTE: obs_dir, nwmretro_file are dynamic and added on the fly
DATAFILE_LIBS = {
    "noah_parameter_dir": f"{MODULE_PARAMETER_FILES_DIR}/noah-owp-modular",
    "ueb_parameter_dir": f"{MODULE_PARAMETER_FILES_DIR}/ueb",
    "lasam_parameter_dir": f"{MODULE_PARAMETER_FILES_DIR}/lasam",
    "lstm_parameter_dir": f"{MODULE_PARAMETER_FILES_DIR}/lstm",
    "ngen_exe_file": NGEN_BIN__LINK,
    "sloth_lib": f"{NGEN_DIR}/extern/sloth/cmake_build/libslothmodel.so",
    "cfe_lib": f"{NGEN_DIR}/extern/cfe/cmake_build/libcfebmi.so",
    "lasam_lib": f"{NGEN_DIR}/extern/LASAM/cmake_build/liblasambmi.so",
    "noah_owp_modular_lib": f"{NGEN_DIR}/extern/noah-owp-modular/cmake_build/libsurfacebmi.so",
    "pet_lib": f"{NGEN_DIR}/extern/evapotranspiration/evapotranspiration/cmake_build/libpetbmi.so",
    "sac_sma_lib": f"{NGEN_DIR}/extern/sac-sma/cmake_build/libsacbmi.so",
    "sft_lib": f"{NGEN_DIR}/extern/SoilFreezeThaw/cmake_build/libsftbmi.so",
    "smp_lib": f"{NGEN_DIR}/extern/SoilMoistureProfiles/cmake_build/libsmpbmi.so",
    "snow_17_lib": f"{NGEN_DIR}/extern/snow17/cmake_build/libsnow17bmi.so",
    "topmodel_lib": f"{NGEN_DIR}/extern/topmodel/cmake_build/libtopmodelbmi.so",
    "ueb_lib": f"{NGEN_DIR}/extern/ueb-bmi/cmake_build/src/libbmiuebcxx.so",
}


SRC_LOG_CONFIG_JSON = "/ngen-app/bin/ngen_rte/run_config/ngen_logging.json"
# Must match config.bashrc
RTE_NGEN_LOG_BEHAVIOR_KEY = "NGEN_LOG_TO_RTE"
# Must match EWTS, nwm-cal-mgr, and nwm-fcst-mgr
NGEN_LOG_DIR_KEY = "NGEN_RESULTS_DIR"
NGEN_STDOUT_STDERR_LOG_FILE_BASENAME = "ngen_stdout_stderr.log"

### These for WCOSS paths
SCRATCH_DIR_OVERRIDE: str | None = None
FORCING_PRODUCT_VERSIONS_PATH: str | None = None
# SCRATCH_DIR_OVERRIDE: str | None = "/foo/bar/scratch"
# FORCING_PRODUCT_VERSIONS_PATH: str | None = (
#     "/ngen-app/bin/ngen_rte/run_config/ngen_forcing_vers.json"
# )
### Parsing the json file if provided
if FORCING_PRODUCT_VERSIONS_PATH is not None:
    with open(FORCING_PRODUCT_VERSIONS_PATH, "r") as f:
        FORCING_PRODUCT_VERSIONS_DICT = json.load(f)
else:
    FORCING_PRODUCT_VERSIONS_DICT = None
