#!/bin/bash

set -euo pipefail
set -x

source config.bashrc

mkdir -p "${REPOS_COMMON_ROOT__HOST}"

SSH_OR_HTTPS=$1
SHALLOW_CLONE=${2:-"full"} # default to full git clone

### Clone repos unless they already exist on disk
function clone_if_not_exists {
    if [ "$SSH_OR_HTTPS" == "ssh" ]; then
        url="git@github.com:NGWPC/${1}.git"
    elif [ "$SSH_OR_HTTPS" == "https" ]; then
        url="https://github.com/NGWPC/${1}.git"
    else
        fatal "Expected 'ssh' or 'https' for position 1 CLI arg, but got: '$SSH_OR_HTTPS'"
    fi

    if test -d "${REPOS_COMMON_ROOT__HOST}/${1}"; then
        info "Already exists: ${REPOS_COMMON_ROOT__HOST}/${1}"
    else
        if [ "$SHALLOW_CLONE" == "shallow" ]; then
            git clone --depth 1 --recurse-submodules "${url}" "${REPOS_COMMON_ROOT__HOST}/${1}"
        else
            git clone --recurse-submodules "${url}" "${REPOS_COMMON_ROOT__HOST}/${1}"
        fi
    fi
    # ( cd "${REPOS_COMMON_ROOT__HOST}/${1}"; git checkout development; git pull --recurse-submodules; git submodule update --init --recursive )
}
clone_if_not_exists "ngen-forcing"
clone_if_not_exists "ngen"
clone_if_not_exists "nwm-fcst-mgr"
clone_if_not_exists "nwm-msw-mgr"
clone_if_not_exists "nwm-cal-mgr"
clone_if_not_exists "nwm-verf"
clone_if_not_exists "nwm-eval-mgr"
clone_if_not_exists "nwm-region-mgr"
clone_if_not_exists "data-assimilation-engine"
clone_if_not_exists "nwm-rte"

exit 0
