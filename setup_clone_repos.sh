#!/bin/bash

set -euo pipefail
set -x

source config.bashrc

mkdir -p "${REPOS_COMMON_ROOT__HOST}"

### Clone repos unless they already exist on disk
function clone_if_not_exists {
    if test -d "${REPOS_COMMON_ROOT__HOST}/${1}"; then
        info "Already exists: ${REPOS_COMMON_ROOT__HOST}/${1}"
    else
        ( cd "${REPOS_COMMON_ROOT__HOST}" && git clone --recurse-submodules "git@github.com:NGWPC/${1}.git" )
    fi
}
clone_if_not_exists "ngen-forcing"
clone_if_not_exists "ngen"
clone_if_not_exists "nwm-fcst-mgr"
clone_if_not_exists "nwm-msw-mgr"
clone_if_not_exists "nwm-cal-mgr"
clone_if_not_exists "nwm-verf"
clone_if_not_exists "nwm-eval-mgr"
clone_if_not_exists "nwm-region-mgr"
clone_if_not_exists "nwm-rte"
