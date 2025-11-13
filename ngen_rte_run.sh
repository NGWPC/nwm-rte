#!/bin/bash
# 
# ngen_rte_run.sh
# 
# This script makes a docker run call to execute a workflow in the RTE Docker image (already built).
# 
# Requirements:
#   Note: ./setup_workspace.sh can be used to download the following data.
# 
#   1. Various data files have been copied from s3 to locations defined in
#       ./config.bashrc and ./setup_workspace.sh, e.g. from
#           s3://ngwpc-hydrofabric
#           s3://ngwpc-forcing
#           s3://ngwpc-dev/
# 
#   2. Repo ngwpc/ngen-forcing has been cloned to ${REPOS_COMMON_ROOT__HOST}/ngen-forcing/ (for BMI config templates)
# 
#   3. Repo ngwpc/nwm-msw-mgr has been cloned to ${REPOS_COMMON_ROOT__HOST}/nwm-msw-mgr/ (for module_parameter_files)
# 


set -euo pipefail
set -x

source config.bashrc

    # time sudo docker run --entrypoint /bin/sh -it \
function docker_run {
    time sudo docker run --entrypoint python \
        -v "${MNT__RUN_NGEN__HOST}:${MNT__RUN_NGEN__CONTAINER_1}" \
        -v "${MNT__RUN_NGEN__HOST}:${MNT__RUN_NGEN__CONTAINER_2}" \
        -v "${MNT__NGEN_FORCING__HOST}:${MNT__NGEN_FORCING__CONTAINER_1}" \
        -v "${MNT__NGEN_FORCING__HOST}:${MNT__NGEN_FORCING__CONTAINER_2}" \
        -v "${MNT__S3_DATA__HOST}:${MNT__S3_DATA__CONTAINER_1}" \
        -v "${MNT__S3_DATA__HOST}:${MNT__S3_DATA__CONTAINER_2}" \
        -v "${MNT__MODULE_PARAM_FILES_DIR__HOST}:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1}" \
        -v "${MNT__MODULE_PARAM_FILES_DIR__HOST}:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_2}" \
        -v "${RUN_NGEN_ROOT__HOST}/data/geo_em_CONUS.nc:/ngen-app/data/esmf_mesh/NWM/domain/geo_em_CONUS.nc" \
        -v "$(pwd)/docker_logs/run:/ngencerf/data/run-logs" \
        -v "$(pwd)/bin_mounted/:/ngen-app/bin/bin_mounted/" \
        \
        --rm ${TARGET_IMAGE_NAME} $*
}

docker_run "/ngen-app/bin/bin_mounted/example_workflow.py"
# docker_run

exit 0
