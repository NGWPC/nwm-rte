#!/bin/bash

set -euo pipefail

### Passed to `docker build` call. Choose from: ["--no-cache", ""]. Has mild impact when using ghcr base.
# CHOICE_CACHE="--no-cache"
CHOICE_CACHE=""

### Choose from: ["ghcr", "build_from_local", "build_from_remote"]
CHOICE_NGEN_SOURCE_MODE="ghcr"
# CHOICE_NGEN_SOURCE_MODE="build_from_local"
# CHOICE_NGEN_SOURCE_MODE="build_from_remote"

### Freeform name tag for image that is built in this process
CHOICE_TARGET_IMAGE_NAME="ngen_rte:`date '+%Y%m%d%H%M%S'`-${CHOICE_NGEN_SOURCE_MODE}"

### Only used when ngen source mode is "build_from_remote". Choose any GitHub tag (or branch name).
CHOICE_NGEN_REMOTE_REPO_TAG="development"

### Only used when ngen image source mode is "ghcr". Choose any ghcr tag, e.g. "latest" or a commit hash.
### This one is based on PR 68 https://github.com/NGWPC/ngen/pull/68: https://github.com/NGWPC/ngen/commit/891e15f1c4121bc1735709fb7782f3fcadf88c43
# CHOICE_NGEN_REMOTE_GHCR_TAG="latest"
CHOICE_NGEN_REMOTE_GHCR_TAG="891e15f1c412"


##### Forecast Manager
### TODO implement this switch (currently need to edit Dockerfile.rte to switch). When implemented, will choose from ["remote", "local"]
# COMPONENT__FCST_MGR__SOURCE_MODE="remote"
# COMPONENT__FCST_MGR__SOURCE_MODE="local"
### Only used when sourcing fcst mgr from GitHub
COMPONENT__FCST_MGR__REMOTE_REPO_TAG="development"

##### Model Setup Workflow Manager
### TODO implement this switch (currently need to edit Dockerfile.rte to switch). When implemented, will choose from ["remote", "local"]
# COMPONENT__MSW_MGR__SOURCE_MODE="remote"
# COMPONENT__MSW_MGR__SOURCE_MODE="local"
### Only used when sourcing mswm from GitHub
# COMPONENT__MSW_MGR__REPO_TAG="development"
COMPONENT__MSW_MGR__REMOTE_REPO_TAG="jwade_NGWPC-8667_historical_bmi_forcing"

##### Calibration Manager
### TODO implement this switch (currently need to edit Dockerfile.rte to switch). When implemented, will choose from ["remote", "local"]
# COMPONENT__CAL_MGR__SOURCE_MODE="remote"
# COMPONENT__CAL_MGR__SOURCE_MODE="local"
### Only used when sourcing calibration manager from GitHub
# COMPONENT__CAL_MGR__REPO_TAG="development"
COMPONENT__CAL_MGR__REMOTE_REPO_TAG="jwade_NGWPC-8667_historical_bmi_forcing"


##### Region Manager
### TODO implement this switch (currently need to edit Dockerfile.rte to switch). When implemented, will choose from ["remote", "local"]
# COMPONENT__REGION_MGR__SOURCE_MODE="remote"
# COMPONENT__REGION_MGR__SOURCE_MODE="local"
### Only used when sourcing region manager from GitHub
COMPONENT__REGION_MGR__REMOTE_REPO_TAG="development"


### Config template mounts from ngen-forcing repo
###   e.g. ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/
MNT__NGEN_FORCING__HOST="${HOME}/ngwpc/ngen-forcing"
MNT__NGEN_FORCING__CONTAINER_1="/ngwpc/ngen-forcing"
MNT__NGEN_FORCING__CONTAINER_2="${MNT__NGEN_FORCING__HOST}"


### Data mounts for common data copied from s3, e.g.:
###     mkdir -p ~/s3/ngwpc-hydrofabric/
###     aws s3 cp s3://ngwpc-hydrofabric/CFE-X_params_2.2.csv ~/s3/ngwpc-hydrofabric/
###     aws s3 cp s3://ngwpc-hydrofabric/deltat.csv ~/s3/ngwpc-hydrofabric/
###     aws s3 cp s3://ngwpc-hydrofabric/gpkg_hl_uri.tgz ~/s3/ngwpc-hydrofabric/
###     aws s3 cp s3://ngwpc-hydrofabric/hydrofabric_data.tgz ~/s3/ngwpc-hydrofabric/
###     aws s3 cp s3://ngwpc-hydrofabric/sac_sma_params_2.2.csv ~/s3/ngwpc-hydrofabric/
###     aws s3 cp s3://ngwpc-hydrofabric/snow17_params_2.2.csv ~/s3/ngwpc-hydrofabric/
###     aws s3 cp s3://ngwpc-hydrofabric/ueb_deltat_2.2.csv ~/s3/ngwpc-hydrofabric/
###     aws s3 sync s3://ngwpc-forcing/aorc_2.2/CONUS/Gage_01123000/ ~/s3/ngwpc-forcing/aorc_2.2/CONUS/Gage_01123000/
MNT__S3_DATA__HOST="${HOME}/s3"
MNT__S3_DATA__CONTAINER_1="/s3"
MNT__S3_DATA__CONTAINER_2="${MNT__S3_DATA__HOST}"


### Data mounts for additional data copied from s3
###   e.g. aws s3 sync s3://ngwpc-dev/jeff.wade/ ~/ngwpc/run_ngen/data/
###   e.g. aws s3 cp s3://ngwpc-dev/kyle.larkin/esmf/geo_em_CONUS.nc ~/ngwpc/run_ngen/data/
MNT__RUN_NGEN__HOST="${HOME}/ngwpc/run_ngen"
MNT__RUN_NGEN__CONTAINER_1="/ngwpc/run_ngen"
MNT__RUN_NGEN__CONTAINER_2="${MNT__RUN_NGEN__HOST}"


##### Additional parameter file mounts, may be needed only for certain branches
MNT__MODULE_PARAM_FILES_DIR__HOST="${HOME}/ngwpc/nwm-msw-mgr/src/mswm/module_parameter_files"
MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1="/ngen-app/nwm-msw-mgr/src/mswm/module_parameter_files"
MNT__MODULE_PARAM_FILES_DIR__CONTAINER_2="${HOME}/ngwpc/nwm-msw-mgr/src/mswm/module_parameter_files"
# MNT__MODULE_PARAM_FILES_DIR__HOST="${HOME}/ngwpc/nwm-cal-mgr/module_parameter_files"
# MNT__MODULE_PARAM_FILES_DIR__CONTAINER="/ngen-app/nwm-cal-mgr/module_parameter_files"


### Logging functions
BASENAME="$(basename "$(readlink -f "$0")")"
function log_to_stderr() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%S%z')] ${BASENAME}: ${LINENO}: $*" >&2; }
function info() { log_to_stderr INFO: $*; }
function error() { log_to_stderr ERROR: $*; }
function fatal() { log_to_stderr FATAL ERROR: $*; exit 1; }
