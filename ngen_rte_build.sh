#!/bin/bash

set -euo pipefail
source config.bashrc
set -x

## 
## \brief
## Build the `ngen` runtime environment Docker image.
## 
## \desc
## Build the `ngen` runtime environment Docker image, applying various OS env vars from `config.bashrc`.
## 
## Can build the `ngen-forcing` and `ngen` base images if not wishing to source `ngen` from an existing GHCR image or an existing local image.
## 
## Components can be installed from GitHub, or from local source code, or skipped.
## 
## The image built is tagged using env var `TARGET_IMAGE_NAME` (typically from `config.bashrc`).
## 
## When the script exits, it echoes the image name and provides a command that can be used to enter the container interactively.
## 
## Alternatively, the user can run `./run.sh` after the build is complete.
## 
## Has 0 positional arguments and 0 named arguments.
## 
## <u>Requirements:</u>
## 
## If configured to install ngwpc packages from local sources instead of from GitHub, then this script assumes this is ran from a sibling directory
## of those repositories (already cloned, checked out, pulled). `./setup_clone_repos.sh` can be used to clone the relevant ngwpc repos.
## 
## \usage ./ngen_rte_build.sh
## 

# DOCKER_BUILDKIT=1 is the default with Docker version 23+.
# Here it is used to enable autodetection of dockerignore file outside of the build context,
# which works when the dockerignore file is the same location and name as the Dockerfile,
# but with the .dockerignore extension added to the end.
export DOCKER_BUILDKIT=1

TIMESTAMP=`date '+%Y%m%d%H%M%S'`


function build_intermediary_image_from_remote_source () {
    # If the repo does not already exist in the tmp location, do a shallow clone of the desired tag/branch.
    # If the repo does exist already, make the clone unshallow, and then check out the desired tag/branch.

    # target_image="ngen:${NGEN_SOURCE_MODE}"
    repo_name=$1  # e.g. "ngen-forcing"
    repo_tag=$2  # e.g. "development" or "3.1.2.1.0"
    dockerfile=$3  # e.g. "Dockerfile" or "Dockerfile.bmi-forcings"
    target_image=$4  # e.g. "ngen-forcing:local-3.1.2.1.0"
    build_arg=$5  # Optional, passed to docker build call. e.g. "" or "NGEN_FORCING_IMAGE_TAG=ngen-forcing:local-3.1.2.1.0"

    source_local_tmp="${REPOS_COMMON_ROOT__HOST}/${repo_name}_tmp"
    # source_local_tmp="${REPOS_COMMON_ROOT__HOST}/${repo_name}"

    git_url="https://github.com/NGWPC/${repo_name}.git"

    if test -d ${source_local_tmp}; then
        info "Pulling ref ${repo_tag} and submodules for ${source_local_tmp}"

        is_shallow=`git -C "${source_local_tmp}" rev-parse --is-shallow-repository`
        if [[ ${is_shallow} == "true" ]]; then
            # It was cloned as shallow earlier, make it unshallow
            ( cd "${source_local_tmp}"; git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"; git fetch --unshallow; )
        fi
        (
            cd "${source_local_tmp}"
            git fetch
            git checkout "${repo_tag}"
            if git symbolic-ref -q HEAD >/dev/null; then
                # On a branch (not a detached head)
                git pull --recurse-submodules
            fi
            git submodule update --init --recursive
        )
    else
        info "Cloning ref ${repo_tag} from ${git_url}"
        git clone --depth 1 --branch ${repo_tag} --recurse-submodules "${git_url}" "${source_local_tmp}"
    fi

    info building image: ${target_image}

    # Build the image, either with or without a build arg.
    if [[ -n "${build_arg}" ]]; then
        # Use the build arg, e.g. for building ngen from ngen-forcing
        ( \
            cd ${source_local_tmp}; sudo docker build -f ${dockerfile} -t ${target_image} --build-arg "${build_arg}" . \
            |& tee "${REPOS_COMMON_ROOT__HOST}/nwm-rte/docker_logs/build/${target_image}-${TIMESTAMP}.log" \
        )
    else
        # No build arg
        ( \
            cd ${source_local_tmp}; sudo docker build -f ${dockerfile} -t ${target_image} . \
            |& tee "${REPOS_COMMON_ROOT__HOST}/nwm-rte/docker_logs/build/${target_image}-${TIMESTAMP}.log" \
        )
    fi

    info built image: ${target_image}
}


# Build ngen base image if specified, otherwise just set var to ghcr URL
if [[ $NGEN_SOURCE_MODE == "ghcr" ]]; then
    NGEN_BASE_IMAGE="ghcr.io/ngwpc/ngen:${NGEN_BASE__REMOTE_GHCR_TAG}"

elif [[ $NGEN_SOURCE_MODE == "existing_local_tag" ]]; then
    NGEN_BASE_IMAGE="${NGEN_BASE__EXISTING_LOCAL_TAG}"

elif [[ $NGEN_SOURCE_MODE == "build_from_local" ]]; then
    NGEN_BASE_IMAGE="ngen:${NGEN_SOURCE_MODE}"
    NGEN_SOURCE_LOCAL="${REPOS_COMMON_ROOT__HOST}/ngen"
    # ./ngen_update_submodules.sh "${NGEN_SOURCE_LOCAL}"
    ( cd ${NGEN_SOURCE_LOCAL}; sudo docker build -t ${NGEN_BASE_IMAGE} . )

elif [[ $NGEN_SOURCE_MODE == "build_from_remote" ]]; then
    if [[ -z "${NGEN_BASE_REMOTE_TAG}" ]]; then
        fatal "NGEN_BASE_REMOTE_TAG cannot be empty when NGEN_SOURCE_MODE=${NGEN_SOURCE_MODE}"
    fi

    NGEN_BASE_IMAGE="ngen:remote-${NGEN_BASE_REMOTE_TAG}"

    ngen_build_arg=""  # Initialize empty, then replace if building forcing from source

    if [[ -n "${FORCING_BASE_REMOTE_TAG}" ]]; then
        # Build forcing first. NOTE: requires that the ngen Dockerfile has an ARG NGEN_FORCING_IMAGE
        build_intermediary_image_from_remote_source \
            "ngen-forcing" \
            "${FORCING_BASE_REMOTE_TAG}" \
            "Dockerfile.bmi-forcings" \
            "ngen-forcing:remote-${FORCING_BASE_REMOTE_TAG}" \
            ""

        ngen_build_arg="NGEN_FORCING_IMAGE=ngen-forcing:remote-${FORCING_BASE_REMOTE_TAG}"
    fi

    # Build ngen
    build_intermediary_image_from_remote_source \
        "ngen" \
        "${NGEN_BASE_REMOTE_TAG}" \
        "Dockerfile" \
        "${NGEN_BASE_IMAGE}" \
        "${ngen_build_arg}"

else
    fatal "Not implemented: NGEN_SOURCE_MODE=${NGEN_SOURCE_MODE}"
fi
# exit 0

# Build RTE image from ngen base image
info "Building image: ${TARGET_IMAGE_NAME}"

# Sanitize the image name for the log file (replace / and : with _)
SAFE_LOG_NAME=$(echo "${TARGET_IMAGE_NAME}" | tr '/:' '__')

sudo docker build -t ${TARGET_IMAGE_NAME} -f Dockerfile.rte ${NO_CACHE} --target ${STAGE} \
    --build-arg TARGET_IMAGE_SOURCE=${TARGET_IMAGE_SOURCE} \
    --build-arg TARGET_IMAGE_VENDOR=${TARGET_IMAGE_VENDOR} \
    --build-arg TARGET_IMAGE_VERSION=${TARGET_IMAGE_VERSION} \
    --build-arg TARGET_IMAGE_REVISION=${TARGET_IMAGE_REVISION} \
    --build-arg TARGET_IMAGE_CREATED=${TARGET_IMAGE_CREATED} \
    --build-arg NGEN_BASE_IMAGE=${NGEN_BASE_IMAGE} \
    --build-arg INSTALL_DEBUGGERS=${INSTALL_DEBUGGERS} \
    --build-arg REPO_TAG_FCST_MGR="${REPO_TAG_FCST_MGR}" \
    --build-arg REPO_TAG_MSW_MGR="${REPO_TAG_MSW_MGR}" \
    --build-arg REPO_TAG_CAL_MGR="${REPO_TAG_CAL_MGR}" \
    --build-arg REPO_TAG_REGION_MGR="${REPO_TAG_REGION_MGR}" \
    --build-arg REPO_TAG_DATA_ASSIM_ENGINE="${REPO_TAG_DATA_ASSIM_ENGINE}" \
    --build-arg REPO_TAG_NGEN_FORCING="${REPO_TAG_NGEN_FORCING}" \
    --build-arg REPO_TAG_VERF="${REPO_TAG_VERF}" \
    --build-arg REPO_TAG_EVAL="${REPO_TAG_EVAL}" \
    ".." \
    |& tee "docker_logs/build/${SAFE_LOG_NAME}-${TIMESTAMP}.log"

info "Built image: ${TARGET_IMAGE_NAME}"
info "Command to start and enter container without executing anything: sudo docker run --entrypoint /bin/bash -it --rm ${TARGET_IMAGE_NAME}"

exit 0
