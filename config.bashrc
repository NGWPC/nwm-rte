#!/bin/bash

set -euo pipefail

### NO_CACHE: Passed to `docker build` call. Choose from: ["--no-cache", ""]. Has mild effect on RTE build speed when using pre-built base ngen image.
# NO_CACHE="--no-cache"
NO_CACHE=""


# If you use this for REPOS_COMMON_ROOT__HOST, then the other repos are assumed to be siblings of this repo
THIS_SCRIPTS_GRANDPARENT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"


### REPOS_COMMON_ROOT__HOST:
###
###     What this variable is for:
###         ./setup_workspace.sh sets up this local directory by downloading data into it and cloning repos into it.
###         ./ngen_rte_build.sh does not use this.
###         ./ngen_rte_run.sh mounts various subdirectories and files from this local directory, into the container, during runtime.
###
###     Choices for this variable:
###         A typical choice for this is ${THIS_SCRIPTS_GRANDPARENT_DIR}, which is equivalent to "${HOME}/ngwpc" if you run this from "${HOME}/ngwpc/nwm-rte"
###         but another location such as "${HOME}/ngwpc__rte" could be used if wanting to isolate the RTE from other work.
###
###         Using ${THIS_SCRIPTS_GRANDPARENT_DIR} guarantees that the setup scripts (`./setup_data.sh` and `./setup_clone_repos.sh`)
###         will copy data and clone repos into the same locations where the build script and run script will look for them.
###     
REPOS_COMMON_ROOT__HOST=${THIS_SCRIPTS_GRANDPARENT_DIR}
# REPOS_COMMON_ROOT__HOST="${HOME}/ngwpc"
# REPOS_COMMON_ROOT__HOST="${HOME}/ngwpc__rte"


RUN_NGEN_ROOT__HOST="${REPOS_COMMON_ROOT__HOST}/run_ngen"
S3_ROOT__HOST="${REPOS_COMMON_ROOT__HOST}/s3"


### NGEN_SOURCE_MODE:
###     Choose from: ["ghcr", "existing_local_tag", "build_from_local", "build_from_remote"]

NGEN_SOURCE_MODE="ghcr"
## Only used when ngen image source mode is "ghcr". Choose any ghcr tag, e.g. "latest" or a commit hash.
# NGEN_BASE__REMOTE_GHCR_TAG="latest"
## This one is based on PR 68 https://github.com/NGWPC/ngen/pull/68: https://github.com/NGWPC/ngen/commit/891e15f1c4121bc1735709fb7782f3fcadf88c43
# NGEN_BASE__REMOTE_GHCR_TAG="891e15f1c412"
## This one is based on PR 58: https://github.com/NGWPC/ngen/pull/58
NGEN_BASE__REMOTE_GHCR_TAG="350dcd08a53e"

# NGEN_SOURCE_MODE="existing_local_tag"
## Only used when ngen image source mode is "existing_local_tag". Choose any existing local image tag.
# NGEN_BASE__EXISTING_LOCAL_TAG="ngen:build_from_remote"

# NGEN_SOURCE_MODE="build_from_remote"
## Only used when ngen source mode is "build_from_remote". Choose any GitHub tag (or branch name).
# NGEN_BASE__REMOTE_REPO_TAG="development"

# NGEN_SOURCE_MODE="build_from_local"


### Freeform name tag for image that is built in this process
# TARGET_IMAGE_NAME="ngen_rte:`date '+%Y%m%d%H%M%S'`-${NGEN_SOURCE_MODE}"
TARGET_IMAGE_NAME="ngen_rte:${NGEN_SOURCE_MODE}"


##### Package: Forecast Manager
### TODO implement this type of switch (currently need to edit Dockerfile.rte to switch). When implemented, will choose from ["remote", "local"]
# COMPONENT__FCST_MGR__SOURCE_MODE="remote"
# COMPONENT__FCST_MGR__SOURCE_MODE="local"
### Only used when sourcing fcst mgr from GitHub
COMPONENT__FCST_MGR__REMOTE_REPO_TAG="development"

##### Package: Model Setup Workflow Manager
### Only used when sourcing mswm from GitHub
COMPONENT__MSW_MGR__REMOTE_REPO_TAG="development"

##### Package: Calibration Manager
### Only used when sourcing calibration manager from GitHub
COMPONENT__CAL_MGR__REMOTE_REPO_TAG="development"

##### Package: Region Manager
### Only used when sourcing region manager from GitHub
### TODO this currently uses shapely 2. Need to either upgrade ngen's shapely, or downgrade this package's shapely to <2
COMPONENT__REGION_MGR__REMOTE_REPO_TAG="development"

##### Package: Verification
### Only used when sourcing verification manager from GitHub
### TODO this currently uses shapely 2. Need to either upgrade ngen's shapely, or downgrade this package's shapely to <2
COMPONENT__VERF__REMOTE_REPO_TAG="development"

#### Evaluation
### Only used when sourcing evaluation manager from GitHub
### TODO this currently uses shapely 2. Need to either upgrade ngen's shapely, or downgrade this package's shapely to <2
COMPONENT__EVAL__REMOTE_REPO_TAG="development"


### Config template mounts from ngen-forcing repo
###   e.g. ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/
MNT__NGEN_FORCING__HOST="${REPOS_COMMON_ROOT__HOST}/ngen-forcing"
MNT__NGEN_FORCING__CONTAINER_1="/ngwpc/ngen-forcing"
MNT__NGEN_FORCING__CONTAINER_2="${MNT__NGEN_FORCING__HOST}"

### Data mounts
MNT__S3_DATA__HOST="${S3_ROOT__HOST}"
MNT__S3_DATA__CONTAINER_1="/s3"
MNT__S3_DATA__CONTAINER_2="${MNT__S3_DATA__HOST}"

### Data mounts
MNT__RUN_NGEN__HOST="${RUN_NGEN_ROOT__HOST}"
MNT__RUN_NGEN__CONTAINER_1="/ngwpc/run_ngen"
MNT__RUN_NGEN__CONTAINER_2="${MNT__RUN_NGEN__HOST}"

#### Parameter file mounts
MNT__MODULE_PARAM_FILES_DIR__HOST="${REPOS_COMMON_ROOT__HOST}/nwm-msw-mgr/src/mswm/module_parameter_files"
MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1="/ngen-app/nwm-msw-mgr/src/mswm/module_parameter_files"
MNT__MODULE_PARAM_FILES_DIR__CONTAINER_2="${REPOS_COMMON_ROOT__HOST}/nwm-msw-mgr/src/mswm/module_parameter_files"


### Logging functions
BASENAME="$(basename "$(readlink -f "$0")")"
function log_to_stderr() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%S%z')] ${BASENAME}: ${LINENO}: $*" >&2; }
function info() { log_to_stderr INFO: $*; }
function error() { log_to_stderr ERROR: $*; }
function fatal() { log_to_stderr FATAL ERROR: $*; exit 1; }
