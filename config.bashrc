#!/bin/bash

set -euo pipefail

### Docker cache directive passed to `docker build` call. Choose from: ["--no-cache", ""]
# NO_CACHE="--no-cache"
NO_CACHE=""

### STAGE: See Dockerfile.rte for acceptable values
# STAGE="ngen_rte_base"
STAGE="ngen_rte_eval_verf"

### Sources of component packages.
### If empty string, package will be skipped (not installed at all).
### If "LOCAL", will install from current state of local code.
### If any other string, will install from GitHub, and the string must be a valid tag, branch, or commit.
REPO_TAG_FCST_MGR="development"
REPO_TAG_MSW_MGR="development"
REPO_TAG_CAL_MGR="development"
REPO_TAG_REGION_MGR="development"
REPO_TAG_DATA_ASSIM_ENGINE="development"
REPO_TAG_NGEN_FORCING=""  # For reinstall of ngen-forcing Python package
REPO_TAG_EVAL="development"
REPO_TAG_VERF="development"

### NGEN_SOURCE_MODE:
### Choose from: ["ghcr", "existing_local_tag", "build_from_local", "build_from_remote"]
### default to "ghcr", as this is used in the GHA Workflow

NGEN_SOURCE_MODE="ghcr"
## Only used when ngen image source mode is "ghcr". Choose any ghcr tag, e.g. "latest" or a commit hash.
NGEN_BASE__REMOTE_GHCR_TAG="latest"

# NGEN_SOURCE_MODE="existing_local_tag"
## Only used when ngen image source mode is "existing_local_tag". Choose any existing local image tag.
# NGEN_BASE__EXISTING_LOCAL_TAG="ngen:localdebug"

# NGEN_SOURCE_MODE="build_from_remote"
## Only used when ngen source mode is "build_from_remote". Choose any GitHub tag (or branch name).
# NGEN_BASE="development"

# NGEN_SOURCE_MODE="build_from_local"

### Freeform name tag for image that is built in this process
TARGET_IMAGE_NAME="ngen_rte:${NGEN_SOURCE_MODE}"

# If you use this for REPOS_COMMON_ROOT__HOST, then the other repos are assumed to be siblings of this repo
THIS_SCRIPTS_GRANDPARENT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

### REPOS_COMMON_ROOT__HOST:
###  What this variable is for:
###      ./setup_clone_repos.sh sets up this local directory and clones "sister" repos into it
###      ./setup_data.sh  downloads data into it 
###      ./ngen_rte_build.sh uses this to find ngen when NGEN_SOURCE_MODE == "build_from_local"
###      ./ngen_rte_run.sh mounts various subdirectories and files from this local directory, into the container, during runtime.
###
###  Choices for this variable:
###      A typical choice for this is ${THIS_SCRIPTS_GRANDPARENT_DIR}, which is equivalent to "${HOME}/ngwpc" if you run this from "${HOME}/ngwpc/nwm-rte"
###      but another location such as "${HOME}/ngwpc__rte" could be used if wanting to isolate the RTE from other work.
###
###      Using ${THIS_SCRIPTS_GRANDPARENT_DIR} guarantees that the setup scripts (`./setup_data.sh` and `./setup_clone_repos.sh`)
###      will copy data and clone repos into the same locations where the build script and run script will look for them.
###     
REPOS_COMMON_ROOT__HOST=${THIS_SCRIPTS_GRANDPARENT_DIR}
# REPOS_COMMON_ROOT__HOST="${HOME}/ngwpc"
# REPOS_COMMON_ROOT__HOST="${HOME}/ngwpc__rte"

RUN_NGEN_ROOT__HOST="${REPOS_COMMON_ROOT__HOST}/run_ngen"
S3_ROOT__HOST="${REPOS_COMMON_ROOT__HOST}/s3"

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

### Region manager data mounts
MNT__NWM_REGION_MGR__INPUT_DATA="${REPOS_COMMON_ROOT__HOST}/nwm-region-mgr/data/inputs"

#### Parameter file mounts
MNT__MODULE_PARAM_FILES_DIR__HOST="${REPOS_COMMON_ROOT__HOST}/nwm-msw-mgr/src/mswm/module_parameter_files"
MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1="/ngen-app/nwm-msw-mgr/src/mswm/module_parameter_files"
MNT__MODULE_PARAM_FILES_DIR__CONTAINER_2="${REPOS_COMMON_ROOT__HOST}/nwm-msw-mgr/src/mswm/module_parameter_files"

### Logging functions
BASENAME="$(basename "$(readlink -f "$0")")"
function log_to_stderr() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%S%z')] ${BASENAME}: ${LINENO}: $*" >&2; }
function info() { log_to_stderr INFO: $*; }
function warning() { log_to_stderr WARNING: $*; }
function error() { log_to_stderr ERROR: $*; }
function fatal() { log_to_stderr FATAL ERROR: $*; exit 1; }
