#!/bin/bash

set -euo pipefail

## 
## \brief
## Configuration file for building and running `nwm-rte`.
## 
## \desc
## This file is `source`'d by multiple shell scripts within `nwm-rte`,
## and its variables control various aspects of the installation / setup / build
## as well as the runtime environment itself (e.g. mount paths).
## 
## \note
## For Pattern `VAR_NAME=${VAR_NAME:-"some_string"}`, values set with this pattern use the existing value if it already exists, e.g. as an OS env var, otherwise they default to "some_string".
## 

## \env GH_ORG GitHub Organization Name
GH_ORG=${GH_ORG:-"NGWPC"}

## \env NO_CACHE Docker cache directive passed to `docker build` call. Choose from: `["--no-cache", ""]`
# NO_CACHE=${NO_CACHE:-"--no-cache"}
NO_CACHE=${NO_CACHE:-""}

## \env STAGE The stage of the docker build sequence to stop at. Choose from: `["ngen_rte_base", "ngen_rte_eval_verf"]`.  See `Dockerfile.rte` for more information
STAGE=${STAGE:-"ngen_rte_base"}
# STAGE=${STAGE:-"ngen_rte_eval_verf"}

## \env INSTALL_DEBUGGERS Passed to ./install_debuggers.sh, causes pip package `debugpy` and dnf package `gdb` to be installed. Choose from: `["NO", "YES"]`
INSTALL_DEBUGGERS=${INSTALL_DEBUGGERS:-"NO"}
# INSTALL_DEBUGGERS=${INSTALL_DEBUGGERS:-"YES"}

## \env NGEN_LOG_TO_RTE Causes ngen's log files to be written to `./ngen_logs` rather than to the realization's dir. Choose from: `["NO", "YES"]`
NGEN_LOG_TO_RTE=${NGEN_LOG_TO_RTE:-"NO"}
# NGEN_LOG_TO_RTE=${NGEN_LOG_TO_RTE:-"YES"}

#### Component Packages
## 
## \desc <u>Choices of Component Packages:</u>
## 
## For each component package (`nwm-msw-mgr`, `nwm-fcst-mgr`, etc), you can choose from an empty string (`""`), or `"LOCAL"`, or any other string.
## 
## * If an empty string `""` is provided, the package will be skipped (will not be installed).
## 
## * If `"LOCAL"` is provided, the package will install from the code currently on disk.
## 
## * If any other string is provided, the package will install from GitHub, and the string must be a valid tag, branch, or commit.
## 
## \caveat `REPO_TAG_NGEN_FORCING` provision causes the ngen-forcing Python package to be reinstalled, but does not affect other aspects of `ngen-forcing` (does not cause a rebuild from the `ngen-forcing` base).
## This does not affect the base image, does not reflect changes to C++ code nor changes to `ngen-forcing/Dockerfile.bmi-forcings`, nor changes to other ngen-forcing build instructions.
## It only causes an optional `pip install` call to be executed on the `ngen-forcing` Python package, after the manager packages have been installed on top of the ngen base image.
## 
## nwm-rte: bf0accd2c86ccac69e9b6c9923b3b57251f07342
## \env REPO_TAG_FCST_MGR Source for `nwm-fcst-mgr`.
REPO_TAG_FCST_MGR=${REPO_TAG_FCST_MGR:-"433f2ca8015574bc0668f4f8df293ed8b90c9a4e"}
## \env REPO_TAG_MSW_MGR Source for `nwm-mswm-mgr`.
REPO_TAG_MSW_MGR=${REPO_TAG_MSW_MGR:-"f13b05f13c19bac2d7a402577dabc7becbdcb120"}
## \env REPO_TAG_CAL_MGR Source for `nwm-cal-mgr`.
REPO_TAG_CAL_MGR=${REPO_TAG_CAL_MGR:-"b9826eefedfeee84bd0c78f0250e2a64252192d2"}
## \env REPO_TAG_REGION_MGR Source for `nwm-region-mgr`.
REPO_TAG_REGION_MGR=${REPO_TAG_REGION_MGR:-""}
## \env REPO_TAG_DATA_ASSIM_ENGINE Source for `nwm-data-assimilation`.
REPO_TAG_DATA_ASSIM_ENGINE=${REPO_TAG_DATA_ASSIM_ENGINE:-""}
## \env REPO_TAG_NGEN_FORCING (Optional). Source for *re-installing* `ngen-forcing` Python package. Note that this does not affect the sourcing of the base image.
REPO_TAG_NGEN_FORCING=${REPO_TAG_NGEN_FORCING:-"82e689d254ed53a5df091c7e7433926cd70d9424"}
## \env REPO_TAG_VERF Source for `nwm-verf`.
REPO_TAG_VERF=${REPO_TAG_VERF:-""}
## \env REPO_TAG_EVAL Source for `nwm-eval-mgr`.
REPO_TAG_EVAL=${REPO_TAG_EVAL:-""}


#### Sourcing of ngen Base
## 
## \env NGEN_SOURCE_MODE Affects the path of building, the choice of the base ngen image. Choose from: `["ghcr", "existing_local_tag", "build_from_local", "build_from_remote"]`
## 
## * `"ghcr"` causes the `ngen` base image to be sourced from an existing GitHub Container Registry image that has already been published to the `ngen` GitHub repository.
## 
## * `"existing_local_tag"` causes the `ngen` base image to be sourced from an existing local image tag.
## 
## * `"build_from_local"` and `"build_from_remote"` cause the `ngen` base image to be built from the bottom up (build ngen-forcing, then build ngen, then add the RTE layers). The former uses the existing state of the codebase currently on disk for `ngen-forcing` and for `ngen`, and the latter uses the provided GH refs for sourcing the codebases of `ngen-forcing` and `ngen`.
## 

NGEN_SOURCE_MODE=${NGEN_SOURCE_MODE:-"ghcr"}
## \env NGEN_BASE__REMOTE_GHCR_TAG (Only used when `NGEN_SOURCE_MODE="ghcr"`). GHCR image tag to use, e.g. `"latest"` or a commit hash.
NGEN_BASE__REMOTE_GHCR_TAG=${NGEN_BASE__REMOTE_GHCR_TAG:-"f8a476e"}

# NGEN_SOURCE_MODE="existing_local_tag"
## \env NGEN_BASE__EXISTING_LOCAL_TAG (Only used when `NGEN_SOURCE_MODE="existing_local_tag"`). Choose any existing local image tag.
NGEN_BASE__EXISTING_LOCAL_TAG=${NGEN_BASE__EXISTING_LOCAL_TAG:-"ngen:localdebug"}

# NGEN_SOURCE_MODE="build_from_local"

# NGEN_SOURCE_MODE="build_from_remote"
## \env FORCING_BASE_REMOTE_TAG Only used when `NGEN_SOURCE_MODE="build_from_remote"`. Source of the `ngen-forcing` codebase. Choose any GitHub ref.
FORCING_BASE_REMOTE_TAG=${FORCING_BASE_REMOTE_TAG:-"development"}
## \env NGEN_BASE_REMOTE_TAG Only used when `NGEN_SOURCE_MODE="build_from_remote"`. Source of the `ngen` codebase. Choose any GitHub ref.
NGEN_BASE_REMOTE_TAG=${NGEN_BASE_REMOTE_TAG:-"development"}

#### Target Image Name
## \env TARGET_IMAGE_NAME Freeform name for output image tag that is built.
TARGET_IMAGE_NAME=${TARGET_IMAGE_NAME:-"ngen_rte_${NGEN_SOURCE_MODE}"}

#### Misc

# OCI Standard labels for Dockerfile.rte image
# See https://specs.opencontainers.org/image-spec/annotations/
TARGET_IMAGE_SOURCE=${TARGET_IMAGE_SOURCE:-"https://github.com/${GH_ORG}/nwm-rte"}
TARGET_IMAGE_VENDOR=${TARGET_IMAGE_VENDOR:-"${GH_ORG}"}
TARGET_IMAGE_VERSION=${TARGET_IMAGE_VERSION:-"latest"}
TARGET_IMAGE_REVISION=${TARGET_IMAGE_REVISION:-"unknown"} # git commit SHA
TARGET_IMAGE_CREATED=${TARGET_IMAGE_CREATED:-"unknown"} # ISO 8601 format, e.g. 2024-01-01T00:00:00Z

## \env THIS_SCRIPTS_GRANDPARENT_DIR The grandparent directory of this current file. When using `REPOS_COMMON_ROOT__HOST=${THIS_SCRIPTS_GRANDPARENT_DIR}`, then the other NWM repos are assumed to be siblings of the `nwm-rte` repo.
THIS_SCRIPTS_GRANDPARENT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

## \env REPOS_COMMON_ROOT__HOST
## 
## * `./setup_clone_repos.sh` sets up this local directory and clones sibling repos into here. `./setup_data.sh` downloads data into here.
## 
## * `./ngen_rte_build.sh` uses this to find `ngen` source code when `NGEN_SOURCE_MODE="build_from_local"`
## 
## * `./ngen_rte_run.sh` mounts various subdirectories and files from this local directory, into the container, during runtime.
##     
## * Choices for this variable:
##     * A typical choice for this is `${THIS_SCRIPTS_GRANDPARENT_DIR}`, which is equivalent to `"${HOME}/${GH_ORG,,}"` if you run this from `"${HOME}/${GH_ORG,,}/nwm-rte"` but another location such as `"${HOME}/${GH_ORG,,}__rte"` could be used if wanting to isolate the RTE from other work.
##     * Using `${THIS_SCRIPTS_GRANDPARENT_DIR}` guarantees that the setup scripts (`./setup_data.sh` and `./setup_clone_repos.sh`) will copy data and clone repos into the same locations where the build script and run script will look for them.
## 
REPOS_COMMON_ROOT__HOST=${THIS_SCRIPTS_GRANDPARENT_DIR}
# REPOS_COMMON_ROOT__HOST="${HOME}/${GH_ORG,,}"

##### Mounts for data
## \env RUN_NGEN_ROOT__HOST Root of the working data associated with running realizations (dirs for realizations and for intermediary data).
RUN_NGEN_ROOT__HOST=${RUN_NGEN_ROOT__HOST:-"${REPOS_COMMON_ROOT__HOST}/run_ngen"}
## \env MNT__RUN_NGEN__HOST Alias for `RUN_NGEN_ROOT__HOST`. Host path mounted by the container.
MNT__RUN_NGEN__HOST="${RUN_NGEN_ROOT__HOST}"
## \env MNT__RUN_NGEN__CONTAINER_1 1st of 2 paths within the container to which the host disk path described by `MNT__RUN_NGEN__HOST` is mounted.
MNT__RUN_NGEN__CONTAINER_1="/ngwpc/run_ngen"
## \env MNT__RUN_NGEN__CONTAINER_2 2nd of 2 paths within the container to which the host disk path described by `MNT__RUN_NGEN__HOST` is mounted.
MNT__RUN_NGEN__CONTAINER_2="${MNT__RUN_NGEN__HOST}"

##### Mounts for parameter files
## \env MNT__MODULE_PARAM_FILES_DIR__HOST Host path to input module parameter files from `nwm-msw-mgr` repository. Mounted by the container.
MNT__MODULE_PARAM_FILES_DIR__HOST="${REPOS_COMMON_ROOT__HOST}/nwm-msw-mgr/src/mswm/module_parameter_files"
## \env MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1 1st of 2 paths within the container to which the host disk path described by `MNT__MODULE_PARAM_FILES_DIR__HOST` is mounted.
MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1="/ngen-app/nwm-msw-mgr/src/mswm/module_parameter_files"
## \env MNT__MODULE_PARAM_FILES_DIR__CONTAINER_2 2nd of 2 paths within the container to which the host disk path described by `MNT__MODULE_PARAM_FILES_DIR__HOST` is mounted.
MNT__MODULE_PARAM_FILES_DIR__CONTAINER_2="${REPOS_COMMON_ROOT__HOST}/nwm-msw-mgr/src/mswm/module_parameter_files"

##### Mounts for forcing configuration
## \env MNT__NGEN_FORCING__HOST Host disk path to `ngen-forcing` repo, for mounting configuration template files from `ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/`.
MNT__NGEN_FORCING__HOST="${REPOS_COMMON_ROOT__HOST}/ngen-forcing"
## \env MNT__NGEN_FORCING__CONTAINER_1 1st of 2 paths within the container to which the host disk path described by `MNT__NGEN_FORCING__HOST` is mounted.
MNT__NGEN_FORCING__CONTAINER_1="/ngwpc/ngen-forcing"
## \env MNT__NGEN_FORCING__CONTAINER_2 2nd of 2 paths within the container to which the host disk path described by `MNT__NGEN_FORCING__HOST` is mounted.
MNT__NGEN_FORCING__CONTAINER_2="${MNT__NGEN_FORCING__HOST}"

##### Mounts for S3 data
## \env S3_ROOT__HOST Root of input data downloaded from s3.
S3_ROOT__HOST=${S3_ROOT__HOST:-"${REPOS_COMMON_ROOT__HOST}/s3"}
## \env MNT__S3_DATA__HOST Alias for `S3_ROOT__HOST`. Host path mounted by the container.
MNT__S3_DATA__HOST="${S3_ROOT__HOST}"
## \env MNT__S3_DATA__CONTAINER_1 1st of 2 paths within the container to which the host disk path described by `MNT__S3_DATA__HOST` is mounted.
MNT__S3_DATA__CONTAINER_1="/s3"
## \env MNT__S3_DATA__CONTAINER_1 2nd of 2 paths within the container to which the host disk path described by `MNT__S3_DATA__HOST` is mounted.
MNT__S3_DATA__CONTAINER_2="${MNT__S3_DATA__HOST}"

##### Mounts for regionalization data
## \env MNT__NWM_REGION_MGR__INPUT_DATA Host path to input data from `nwm-region-mgr` repository for regionalization workflows. Mounted by the container.
MNT__NWM_REGION_MGR__INPUT_DATA="${REPOS_COMMON_ROOT__HOST}/nwm-region-mgr/data/inputs"

### Logging functions
BASENAME="$(basename "$(readlink -f "$0")")"
function log_to_stderr() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%S%z')] ${BASENAME}: ${LINENO}: $*" >&2; }
function info() { log_to_stderr INFO: $*; }
function warning() { log_to_stderr WARNING: $*; }
function error() { log_to_stderr ERROR: $*; }
function fatal() { log_to_stderr FATAL ERROR: $*; exit 1; }
