#!/bin/bash

set -euo pipefail

## 
## \brief
## Install a Python package, with options, and write git info json. Used by `Dockerfile.rte`
## 
## \desc
## Install a Python package, with options for the python environment, local vs remote, tag, and "extras". Used by `Dockerfile.rte`.
## 
## Also call `add_git_info.py` to dump the package's git info to a json file.
## 
## Treats ngen-forcing reinstall as special since it necessarily is already installed in the base image,
## so if it is specified here, it receives a `--force-reinstall` flag.
## 
## Has 4 positional arguments and 0 named arguments.
## 
## \option python_exe
## The python executable to use for installation
## 
## \option repo_name
## The name of the repository to be installed
## 
## \option repo_remote_tag
## If "LOCAL", then install from local code. If empty string, skip installation. If other string, install that ref (tag, branch, or commit) from GitHub.
## 
## \option extras
## Optional extras to include in the pip install directive, e.g. `pip install package_name[extras]`
## 
## \usage ./install_package.sh python nwm-region-mgr development "[parreg]"
## 

python_exe=$1
repo_name=$2
repo_remote_tag=$3
extras=$4

if [ "$repo_remote_tag" = "LOCAL" ]; then
    echo "Installing '${repo_name}' from local with extras '${extras}'"
    tar --exclude=".venv" -zcf "/tmp/${repo_name}.tgz" -C "/src_ngwpc" "${repo_name}"
    (set -x; ${python_exe} -m pip install /tmp/${repo_name}.tgz${extras})
    rm /tmp/${repo_name}.tgz
    ${python_exe} add_git_info.py --local_repo_path "/src_ngwpc/${repo_name}" --output_dir "/ngen-app/git-info"

# elif tag is not empty
elif [ -n "$repo_remote_tag" ]; then
    echo "Installing '${repo_name}' from GitHub at tag '${repo_remote_tag}' with extras '${extras}'"

    flags=()
    if [ "$repo_name" = "ngen-forcing" ]; then
        flags+=("--force-reinstall")
    fi

    if [ -n "$extras" ]; then
        (set -x; ${python_exe} -m pip install "${flags[@]}" "${repo_name}${extras} @ git+https://github.com/NGWPC/${repo_name}@${repo_remote_tag}")
    else
        (set -x; ${python_exe} -m pip install "${flags[@]}" "https://github.com/NGWPC/${repo_name}/archive/${repo_remote_tag}.tar.gz")
    fi
    # (set -x; ${python_exe} -m pip install "${repo_name}${extras} @ git+https://github.com/NGWPC/${repo_name}@${repo_remote_tag}")
    ${python_exe} add_git_info.py --remote_repo_name "${repo_name}" --remote_branch "${repo_remote_tag}" --output_dir "/ngen-app/git-info"

# tag is empty
else
    echo "WARNING: not installing: '${repo_name}'"
fi
