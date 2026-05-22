#!/bin/bash

set -euo pipefail

source config.bashrc

## 
## \brief
## Script and sourceable function for running the `ngen` runtime environment Docker image.
## 
## \desc
## Run the `ngen` runtime environment Docker image. Requires that the image has already been built.
## 
## The function `docker_run` is sourced by and called by other scripts in the repository such as `./run_default.sh`, `./run_calib.sh`, `./run_fcst.sh`, and `./run_tests.sh`.
##
## When run as a script, causes the user to enter the container shell interactively.
## 
## Various OS env vars are applied from `config.bashrc`. Notably `TARGET_IMAGE_NAME` is the image that is sourced (must have already been built) and launched as a container.
## 
## Various mount paths are also applied, some defined in `config.bashrc` and others defined in `./run.sh` itself.
##     * Input data paths
##     * Output data paths from previous runs
##     * Scripts from `./bin_mounted/`
##     * Cached files from `./devcontainer/tmp/`
## 
## This script has 0 positional arguments and 0 named arguments. See the description for function `docker_run`,
## which is typically sourced by other scripts and ran externally.
## 
## <u>Requirements:</u>
## 
## The `ngen` runtime environment image (defined by `TARGET_IMAGE_NAME`) has already been built.
## 
## The various repositories and input data needed to run are available and mountable (see `./setup_clone_repos.sh`, `./setup_data.sh`, `./setup_data_one_gage.sh`).
## 
## \usage ./run.sh
## \usage source ./run.sh && docker_run python "/path/to/script.py" --arg_for_script
## 
## \function docker_run
## \function-desc Start the `ngen` runtime environment container with various mounts applied. Either run in an interactive terminal, or run a specific command and exit. If arguments are provided, then the 1st argument is the entrypoint command, and all subsequent arguments are arguments for that entrypoint command.  See usage examples in `./run_default.sh`, etc.
## \function-argument entrypoint If `"/bin/sh"`, then start an interactive session. Else, run the provided command and provide the extra arguments as the arguments to that command.
## \function-argument * Any number of extra arguments, provided to the `entrypoint` command.
## 

function docker_run {
    entrypoint=$1

    if [ "$entrypoint" = "/bin/sh" ]; then
        interactive_terminal="-it"
    else
        interactive_terminal=""
    fi

    time sudo docker run --entrypoint "${entrypoint}" ${interactive_terminal} \
        -v "$(pwd)/bin_mounted/:/ngen-app/bin/bin_mounted/" \
        -w "/ngen-app/bin/bin_mounted/" \
        \
        -v "${MNT__RUN_NGEN__HOST}:${MNT__RUN_NGEN__CONTAINER}" \
        \
        -v "${MNT__RUN_NGEN__HOST}/data/esmf_mesh/:/ngen-app/data/esmf_mesh/" \
        -v "${MNT__RUN_NGEN__HOST}/data/scratch:/ngen-app/data/scratch" \
        -v "${MNT__RUN_NGEN__HOST}/configs:/ngen-app/data/configs" \
        -v "${MNT__RUN_NGEN__HOST}/data/raw_input:/ngen-app/data/raw_input" \
        -v "${MNT__RUN_NGEN__HOST}/data:/ngencerf/data/bmi_forcing_work" \
        -v "${MNT__RUN_NGEN__HOST}/data/ngen-cal-work:/ngencerf/data/ngen-cal-work" \
        -v "${MNT__RUN_NGEN__HOST}/data/ngen-static-files:/ngencerf/data/ngen-static-files" \
        \
        -v "${MNT__S3_DATA__HOST}:${MNT__S3_DATA__CONTAINER}" \
        -v "$(pwd)/docker_logs/run:/ngencerf/data/run-logs" \
        -v "$(pwd)/ngen_logs:/ngen-app/rte_ngen_logs" \
        -v "$(pwd)/.devcontainer/tmp:/tmp" \
        -e NGEN_LOG_TO_RTE=${NGEN_LOG_TO_RTE} \
        \
        -v "${REPOS_COMMON_ROOT__HOST}/nwm-automation-scripts/:/ngen-app/nwm-automation-scripts/" \
        \
        --rm ${TARGET_IMAGE_NAME} "${@:2}"
}

# Only run if not being sourced (allows sourcing for docker_run function reuse in GHA workflow)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    docker_run /bin/sh
    exit 0
fi
