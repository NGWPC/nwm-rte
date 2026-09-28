#!/bin/bash

set -euo pipefail

source ./config.bashrc

if [[ $# -gt 1 ]]; then
    echo "ERROR: too many arguments. Usage: $0 [target-image-name]" >&2
    exit 2
fi

DOCKERFILE=nwm-rte/Dockerfile.rte
NGEN_BASE_IMAGE=ghcr.io/${GH_ORG,,}/ngen:latest
TARGET_IMAGE_NAME="${1:-ngen_rte_ghcr:podman-test}"


function build_rte(){
    # Authenticate add_git_info.py's GitHub API calls to avoid shared-runner rate limits.
    local secret_args=()
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        secret_args=(--secret id=github_token,env=GITHUB_TOKEN)
    fi
    (
    cd ..
    podman build \
        --format docker \
        "${secret_args[@]}" \
        --build-arg GH_ORG=${GH_ORG} \
        --build-arg INSTALL_DEBUGGERS=${INSTALL_DEBUGGERS} \
        --build-arg NGEN_BASE_IMAGE=${NGEN_BASE_IMAGE} \
        --build-arg REPO_TAG_FCST_MGR=${REPO_TAG_FCST_MGR} \
        --build-arg REPO_TAG_MSW_MGR=${REPO_TAG_MSW_MGR} \
        --build-arg REPO_TAG_CAL_MGR=${REPO_TAG_CAL_MGR} \
        --build-arg REPO_TAG_REGION_MGR=${REPO_TAG_REGION_MGR} \
        --build-arg REPO_TAG_DATA_ASSIM_ENGINE=${REPO_TAG_DATA_ASSIM_ENGINE} \
        --build-arg REPO_TAG_NGEN_FORCING=${REPO_TAG_NGEN_FORCING} \
        --build-arg REPO_TAG_EWTS=${REPO_TAG_EWTS} \
        --build-arg REPO_TAG_EVAL=${REPO_TAG_EVAL} \
        --build-arg REPO_TAG_ECF_TASK_MGR=${REPO_TAG_ECF_TASK_MGR} \
        --target ${STAGE} \
        -f "${DOCKERFILE}" \
        -t "${TARGET_IMAGE_NAME}" \
        .
    )
}


function run_pytest() {
    podman run --rm --entrypoint "/ngen-app/ngen-python/bin/python" \
    -v "$(pwd)/bin_mounted/ngen_rte/:/ngen-app/bin/ngen_rte/" \
    -w "/ngen-app/bin/ngen_rte" \
    -e RTE_EWTS_ENABLED=${RTE_EWTS_ENABLED} \
    "${TARGET_IMAGE_NAME}" \
    -m pytest
}

./setup_clone_repos.sh https shallow
build_rte
run_pytest
