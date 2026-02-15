from datetime import datetime, timedelta

from calib.strategy import (
    Objective as CalObjective,
    Algorithm as CalOptimizationAlgo,
)


DIR_FORCING_RAW_INPUT = "/ngen-app/data/raw_input"


### .config section [Forcing]
DEFAULT_FORECAST_RUN_NAME = "fcst_run1"

FORCING_PROVIDER_DEFAULT = "bmi"
FORCING_PROVIDER_CHOICES = [FORCING_PROVIDER_DEFAULT, "csv"]

# For CSV forcing
CSV_FORCING_DIR_FORMAT = "/s3/ngwpc-forcing/aorc_2.2/{global_domain}/Gage_{gage_id}/"
# For BMI forcing
FORCING_TEMPLATE_DIR = "/ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/"
FORCING_ROOT_DIR = "/ngen-app/data"
DT_START_FORECAST = datetime(year=2025, month=9, day=15, hour=0, minute=0, second=0)
DT_START_COLDSTART = DT_START_FORECAST - timedelta(days=2)
DT_END_COLDSTART = DT_START_FORECAST


### .config section [General]
DEFAULT_GAGE_ID = "01123000"
DEFAULT_GAGE_VINTAGE = "2025_Mar_14_21_14_37"

MODELS = "noah-owp-modular,cfe-s"
# MODELS = "snow-17,noah-owp-modular,smp,lasam,t-route"
DEFAULT_MAIN_DIR = "/ngwpc/run_ngen"


### .config section [Calibration]
CALIB_OBJECTIVE_FUNCTION = CalObjective.kge
CALIB_OPTIMIZATION_ALGO = CalOptimizationAlgo.dds
CALIB_PARAMETERS_DIR = f"{DEFAULT_MAIN_DIR}/data/calib_params_tab_delimited"
CALIB_ITER_START = 0
CALIB_ITER_COUNT = 2
CALIB_SAVE_PLOT_ITER_FREQ = 1
# Only needed for optimization algo PSO and GWO
CALIB_SWARM_SIZE=3
# Only needed for optimization algo PSO 
CALIB_PSO_C1=2
CALIB_PSO_C2=2
CALIB_PSO_W=0.7
# Timing
CALIB_SIM_START_DEFAULT = datetime(year=2013, month=7, day=25, hour=0, minute=0, second=0)
CALIB_SIM_DURATION_DEFAULT = timedelta(hours=47)
CALIB_EVAL_DELAYMENT_DEFAULT = timedelta(hours=0)  # Gets added
VALID_SIM_ADVANCEMENT_DEFAULT = timedelta(hours=0)  # Gets subtracted
VALID_EVAL_CURTAILMENT_DEFAULT = timedelta(hours=0)  # Gets subtracted


### .config section [DataFile]
MODULE_PARAMETER_FILES_DIR = "/ngen-app/nwm-msw-mgr/src/mswm/module_parameter_files"
NGEN_DIR = "/ngen-app/ngen"
HYDROFABRIC_DIR = "/s3/ngwpc-hydrofabric"


### .config section [Parallel]
DEFAULT_NPROCS = 1


### Test settings
### See this for full list of forcing configuration types: mswm.utils.input_configuration.mswm_valid_configs
FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT = ["short_range", "standard_ana", "medium_range_blend"]
# FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT = ["short_range"]
FORECAST_FORCING_CONFIGURATION_TYPES__ALL = [
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

CALIB_FORCING_CONFIGURATION_TYPE_DEFAULT = "aorc"
CALIB_FORCING_CONFIGURATION_TYPES = [
    "nwm",
    CALIB_FORCING_CONFIGURATION_TYPE_DEFAULT,
]

CALIB_GLOBAL_DOMAIN_DEFAULT = "CONUS"
CALIB_GLOBAL_DOMAIN_CHOICES = [
    CALIB_GLOBAL_DOMAIN_DEFAULT,
    "Alaska",
    "Hawaii",
    "Puerto_Rico",
    "GL",  # Guam / Luta
]

FORCING_STATIC_DIR_DEFAULT = "/ngen-app/data"

# For construction of DataFileConfig
DATAFILE_LIBS = {
    "noah_parameter_dir": f"{MODULE_PARAMETER_FILES_DIR}/noah-owp-modular",
    "ueb_parameter_dir": f"{MODULE_PARAMETER_FILES_DIR}/ueb",
    "lasam_parameter_dir": f"{MODULE_PARAMETER_FILES_DIR}/lasam",
    "lstm_parameter_dir": f"{MODULE_PARAMETER_FILES_DIR}/lstm",
    "sac_sma_parameter_dir": HYDROFABRIC_DIR,
    "snow_17_parameter_dir": HYDROFABRIC_DIR,
    "attributes_file": f"{DEFAULT_MAIN_DIR}/data/conus_model_attributes.parquet",
    "ngen_exe_file": f"{NGEN_DIR}/cmake_build/ngen",
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
