#!/bin/bash
#
# To be ran from docker build context where ngwpc source code (repositories) have been mounted to /tmp/src_ngwpc/
# Overall configuration is taken from config.bashrc, and the CLI arg specifies which stage is being built ("base" or "eval_verf").
#

set -euo pipefail

echo "Sourcing config.bashrc"
source /src_ngwpc/nwm-rte/config.bashrc

THIS_STAGE=$1

function install_package() {
    python_exe=$1
    repo_name=$2
    repo_remote_tag=$3
    extras=$4

    if [ "$repo_remote_tag" = "LOCAL" ]; then
        info "Installing repo '${repo_name}' from local with extras '${extras}'"
        tar zcf "/tmp/${repo_name}.tgz" -C "/src_ngwpc" "${repo_name}" \
            && (set -x; ${python_exe} -m pip -q install /tmp/${repo_name}.tgz${extras}) \
            && rm /tmp/${repo_name}.tgz
        ${python_exe} add_git_info.py --local_repo_path "/src_ngwpc/${repo_name}" --output_dir "/ngen-app/git-info"

    # elif not empty
    elif [ -n "$repo_remote_tag" ]; then
        info "Installing repo '${repo_name}' from GitHub at tag '${repo_remote_tag}' with extras '${extras}'"
        if [ -n "$extras" ]; then
            (set -x; ${python_exe} -m pip -q install "${repo_name}${extras} @ git+https://github.com/NGWPC/${repo_name}@${repo_remote_tag}")
        else
            (set -x; ${python_exe} -m pip -q install "https://github.com/NGWPC/${repo_name}/archive/${repo_remote_tag}.tar.gz")
        fi
        # (set -x; ${python_exe} -m pip -q install "${repo_name}${extras} @ git+https://github.com/NGWPC/${repo_name}@${repo_remote_tag}")
        ${python_exe} add_git_info.py --remote_repo_name "${repo_name}" --remote_branch "${repo_remote_tag}" --output_dir "/ngen-app/git-info"

    # empty
    else
        warning "NOT INSTALLING REPO '${repo_name}'"
    fi
}


info "Installing packages for stage: '$THIS_STAGE'..."

if [ "$THIS_STAGE" = "base" ]; then
    install_package "python" "nwm-fcst-mgr" "${COMPONENT__FCST_MGR__REMOTE_REPO_TAG}" ""
    install_package "python" "nwm-msw-mgr" "${COMPONENT__MSW_MGR__REMOTE_REPO_TAG}" ""
    install_package "python" "nwm-cal-mgr" "${COMPONENT__CAL_MGR__REMOTE_REPO_TAG}" ""
    install_package "python" "nwm-region-mgr" "${COMPONENT__REGION_MGR__REMOTE_REPO_TAG}" "[parreg]"
    install_package "python" "data-assimilation-engine" "${COMPONENT__DATA_ASSIM_ENGINE__REMOTE_REPO_TAG}" ""
    install_package "python" "ngen-forcing" "${COMPONENT__NGEN_FORCING__REMOTE_REPO_TAG}" ""

elif [ "$THIS_STAGE" = "eval_verf" ]; then
    install_package "/ngen-app/venvs/eval_verf/bin/python" "nwm-verf" "${COMPONENT__VERF__REMOTE_REPO_TAG}" ""
    install_package "/ngen-app/venvs/eval_verf/bin/python" "nwm-eval-mgr" "${COMPONENT__EVAL__REMOTE_REPO_TAG}" ""

else
    fatal "Error: Invalid value for CLI arg for stage: '$THIS_STAGE'"
fi

info "Done installing packages for stage: '$THIS_STAGE'."
