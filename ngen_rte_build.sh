#!/bin/bash
# 
# ngen_rte_build.sh
# 
# This script builds the ngen base image (or sources it from existing ghcr image),
# then adds components such as mswm, fcst mgr, cal mgr, etc. to that image,
# 
# See config.bashrc for configuration. Components can be installed from GitHub or from local source code.
# 
# Requirements:
#   Note: ./setup_clone_repos.sh can be used to clone the following repos.
#   
#   If the Dockerfile is set up to install packages such as nwm-fcst-mgr, nwm-cal-mgr, nwm-msw-mgr, and others
#   from local sources instead of from GitHub, then this script assumes this is ran from a sibling directory
#   of those repositories (already cloned, checked out, pulled).
#

set -euo pipefail
set -x

source config.bashrc

# DOCKER_BUILDKIT=1 is the default with Docker version 23+.
# Here it is used to enable autodetection of dockerignore file outside of the build context,
# which works when the dockerignore file is the same location and name as the Dockerfile,
# but with the .dockerignore extension added to the end.
export DOCKER_BUILDKIT=1

TIMESTAMP=`date '+%Y%m%d%H%M%S'`

### Build ngen base image if specified, otherwise just set var to ghcr URL
if [[ $NGEN_SOURCE_MODE == "ghcr" ]]; then
    NGEN_BASE_IMAGE="ghcr.io/ngwpc/ngen:${NGEN_BASE__REMOTE_GHCR_TAG}"

elif [[ $NGEN_SOURCE_MODE == "existing_local_tag" ]]; then
    NGEN_BASE_IMAGE="${NGEN_BASE__EXISTING_LOCAL_TAG}"

elif [[ $NGEN_SOURCE_MODE == "build_from_local" ]]; then
    NGEN_BASE_IMAGE="ngen:${NGEN_SOURCE_MODE}"
    NGEN_SOURCE_LOCAL="${REPOS_COMMON_ROOT__HOST}/ngen"
    # ./ngen_update_submodules.sh "${NGEN_SOURCE_LOCAL}"
    ( cd ${NGEN_SOURCE_LOCAL} && sudo docker build -t ${NGEN_BASE_IMAGE} . )

elif [[ $NGEN_SOURCE_MODE == "build_from_remote" ]]; then
    NGEN_BASE_IMAGE="ngen:${NGEN_SOURCE_MODE}"
    NGEN_SOURCE_LOCAL="${REPOS_COMMON_ROOT__HOST}/ngen_tmp"
    NGEN_GIT_URL="https://github.com/NGWPC/ngen.git"
    if test -d ${NGEN_SOURCE_LOCAL}; then
        info "Pulling branch ${NGEN_BASE__REMOTE_REPO_TAG} and submodules from ${NGEN_SOURCE_LOCAL}"
        ( \
            cd ${NGEN_SOURCE_LOCAL} && \
            git fetch && \
            git checkout ${NGEN_BASE__REMOTE_REPO_TAG} && \
            git pull --recurse-submodules && \
            git submodule update --init --recursive \
        )
    else
        info "Cloning branch ${NGEN_BASE__REMOTE_REPO_TAG} from ${NGEN_GIT_URL}"
        git clone --branch ${NGEN_BASE__REMOTE_REPO_TAG} --recurse-submodules "${NGEN_GIT_URL}" "${NGEN_SOURCE_LOCAL}"
    fi
    # ./ngen_update_submodules.sh "${NGEN_SOURCE_LOCAL}"
    ( cd ${NGEN_SOURCE_LOCAL} && sudo docker build -t ${NGEN_BASE_IMAGE} . )

else
    fatal "Not implemented: NGEN_SOURCE_MODE=${NGEN_SOURCE_MODE}"
fi
# exit 0

### Build RTE image from ngen base image
info "Building image: ${TARGET_IMAGE_NAME}"
sudo docker build -t ${TARGET_IMAGE_NAME} -f Dockerfile.rte ${NO_CACHE} --target ${STAGE} \
    --build-arg NGEN_BASE_IMAGE=${NGEN_BASE_IMAGE} \
    --build-arg REPO_TAG__FCST_MGR="${COMPONENT__FCST_MGR__REMOTE_REPO_TAG}" \
    --build-arg REPO_TAG__MSW_MGR="${COMPONENT__MSW_MGR__REMOTE_REPO_TAG}" \
    --build-arg REPO_TAG__CAL_MGR="${COMPONENT__CAL_MGR__REMOTE_REPO_TAG}" \
    --build-arg REPO_TAG__REGION_MGR="${COMPONENT__REGION_MGR__REMOTE_REPO_TAG}" \
    --build-arg REPO_TAG__VERF_MGR="${COMPONENT__VERF__REMOTE_REPO_TAG}" \
    --build-arg REPO_TAG__EVAL_MGR="${COMPONENT__EVAL__REMOTE_REPO_TAG}" \
    --build-arg REPO_TAG__DATA_ASSIM_ENGINE="${COMPONENT__DATA_ASSIM_ENGINE__REMOTE_REPO_TAG}" \
    --build-arg REPO_TAG__NGEN_FORCING="${COMPONENT__NGEN_FORCING__REMOTE_REPO_TAG}" \
    ".." \
    |& tee "docker_logs/build/${TARGET_IMAGE_NAME}-${TIMESTAMP}.log"

info "Built image: ${TARGET_IMAGE_NAME}"
info "Command to start and enter container without executing anything: sudo docker run --entrypoint /bin/bash -it --rm ${TARGET_IMAGE_NAME}"

exit 0
