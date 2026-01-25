#!/bin/bash
#
# To be ran from docker build context where ngwpc source code (repositories) have been mounted to /src_ngwpc/
#

set -euo pipefail

python_exe=$1
repo_name=$2
repo_remote_tag=$3
extras=$4

if [ "$repo_remote_tag" = "LOCAL" ]; then
    echo "Installing '${repo_name}' from local with extras '${extras}'"
    tar zcf "/tmp/${repo_name}.tgz" -C "/src_ngwpc" "${repo_name}" \
        && (set -x; ${python_exe} -m pip -q install /tmp/${repo_name}.tgz${extras}) \
        && rm /tmp/${repo_name}.tgz
    ${python_exe} add_git_info.py --local_repo_path "/src_ngwpc/${repo_name}" --output_dir "/ngen-app/git-info"

# elif tag is not empty
elif [ -n "$repo_remote_tag" ]; then
    echo "Installing '${repo_name}' from GitHub at tag '${repo_remote_tag}' with extras '${extras}'"
    if [ -n "$extras" ]; then
        (set -x; ${python_exe} -m pip -q install "${repo_name}${extras} @ git+https://github.com/NGWPC/${repo_name}@${repo_remote_tag}")
    else
        (set -x; ${python_exe} -m pip -q install "https://github.com/NGWPC/${repo_name}/archive/${repo_remote_tag}.tar.gz")
    fi
    # (set -x; ${python_exe} -m pip -q install "${repo_name}${extras} @ git+https://github.com/NGWPC/${repo_name}@${repo_remote_tag}")
    ${python_exe} add_git_info.py --remote_repo_name "${repo_name}" --remote_branch "${repo_remote_tag}" --output_dir "/ngen-app/git-info"

# tag is empty
else
    echo "WARNING: not installing: '${repo_name}'"
fi
