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
## Has 7 positional arguments and 0 named arguments.
## 
## \option python_exe
## The python executable to use for installation
## 
## \option gh_org
## The GitHub organization name
## 
## \option repo_name
## The name of the repository to be installed
## 
## \option distribution
## The name of the distribution to be installed (often the same as the repository name, but not always).
## 
## \option repo_remote_tag
## If "LOCAL", then install from local code. If empty string, skip installation. If other string, install that ref (tag, branch, or commit) from GitHub.
## 
## \option extras
## Optional extras to include in the pip install directive, e.g. `pip install package_name[extras]`
##
## \option repo_subdirectory
## Optional subdirectory within the repo to install from, e.g. for `pip install package_name @ git+https://github.com/org/repo@tag#subdirectory=subdir`
##
## \usage ./install_package.sh python nwm-region-mgr development "[parreg]"
## 

flags=()
subdirectory=""
git_info_output_dir="/ngen-app/git-info"


python_exe=$1
gh_org=$2
repo_name=$3
distribution=$4
repo_remote_tag=$5
extras=${6:-}
repo_subdirectory=${7:-}

if [ -n "$repo_subdirectory" ]; then
    subdirectory="#subdirectory=${repo_subdirectory}"
fi

if [ "$repo_name" = "ngen-forcing" ]; then
    # force-reinstall nwm-ewts since it is already installed in the base image.
    flags+=("--force-reinstall")
elif [ "$repo_name" = "nwm-ewts" ]; then
    # force-reinstall nwm-ewts since it is already installed in the base image.
    flags+=("--force-reinstall")
fi


if [ "$repo_remote_tag" = "LOCAL" ]; then
    echo "Installing '${repo_name}' from local with extras '${extras}'"
    tar --exclude=".venv" -zcf "/tmp/${repo_name}.tgz" -C "/src/${gh_org}" "${repo_name}"
    (set -x; ${python_exe} -m pip install "${distribution}${extras:+$extras} @ file:///tmp/${repo_name}.tgz${subdirectory}")
    rm /tmp/${repo_name}.tgz
    ${python_exe} add_git_info.py --gh_org ${gh_org} --local_repo_path "/src/${gh_org}/${repo_name}" --output_dir "${git_info_output_dir}"

# elif tag is not empty
elif [ -n "$repo_remote_tag" ]; then
    echo "Installing '${repo_name}' from GitHub at tag '${repo_remote_tag}' with extras '${extras}'"
    (set -x; ${python_exe} -m pip install "${flags[@]}" "${distribution}${extras:+$extras} @ git+https://github.com/${gh_org}/${repo_name}@${repo_remote_tag}${subdirectory}")
    ${python_exe} add_git_info.py --gh_org ${gh_org} --remote_repo_name "${repo_name}" --remote_branch "${repo_remote_tag}" --output_dir "${git_info_output_dir}"

# tag is empty
else
    echo "WARNING: not installing: '${repo_name}'"
fi
