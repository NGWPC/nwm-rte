#!/bin/bash

set -euo pipefail

source config.bashrc


function docker_run {
    entrypoint=$1

    if [ "$entrypoint" = "/bin/sh" ]; then
        interactive_terminal="-it"
    else
        interactive_terminal=""
    fi

    time sudo docker run --entrypoint "${entrypoint}" ${interactive_terminal} \
        -v "${MNT__RUN_NGEN__HOST}:${MNT__RUN_NGEN__CONTAINER_1}" \
        -v "${MNT__RUN_NGEN__HOST}:${MNT__RUN_NGEN__CONTAINER_2}" \
        \
        -v "${MNT__RUN_NGEN__HOST}/data/esmf_mesh/:/ngen-app/data/esmf_mesh/" \
        -v "${MNT__RUN_NGEN__HOST}/data/scratch:/ngen-app/data/scratch" \
        -v "${MNT__RUN_NGEN__HOST}/configs:/ngen-app/data/configs" \
        -v "${MNT__RUN_NGEN__HOST}/data/raw_input:/ngen-app/data/raw_input" \
        -v "${MNT__RUN_NGEN__HOST}/data:/ngencerf/data/bmi_forcing_work" \
        -v "${MNT__RUN_NGEN__HOST}/data/ngen-cal-work:/ngencerf/data/ngen-cal-work" \
        -v "${MNT__RUN_NGEN__HOST}/data/ngen-static-files:/ngencerf/data/ngen-static-files" \
        -v "${MNT__RUN_NGEN__HOST}/kge_dds:/ngen-app/data/run_ngen" \
        \
        -v "${MNT__NGEN_FORCING__HOST}:${MNT__NGEN_FORCING__CONTAINER_1}" \
        -v "${MNT__NGEN_FORCING__HOST}:${MNT__NGEN_FORCING__CONTAINER_2}" \
        -v "${MNT__S3_DATA__HOST}:${MNT__S3_DATA__CONTAINER_1}" \
        -v "${MNT__S3_DATA__HOST}:${MNT__S3_DATA__CONTAINER_2}" \
        -v "${MNT__MODULE_PARAM_FILES_DIR__HOST}:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1}" \
        -v "${MNT__MODULE_PARAM_FILES_DIR__HOST}:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_2}" \
        -v "$(pwd)/docker_logs/run:/ngencerf/data/run-logs" \
        -v "$(pwd)/bin_mounted/:/ngen-app/bin/bin_mounted/" \
        -v "$(pwd)/.devcontainer/tmp:/tmp" \
        \
        --rm ${TARGET_IMAGE_NAME} "${@:2}"
}

# Only run if not being sourced (allows sourcing for docker_run function reuse in GHA workflow)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    docker_run /bin/sh
    exit 0
fi
