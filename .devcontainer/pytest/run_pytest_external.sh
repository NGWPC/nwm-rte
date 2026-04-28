#!/bin/bash

set -euo pipefail

source config.bashrc

## 
## \brief
## Runs an ephemeral docker container to execute `python -m pytest` and quit. An alternative to running `pytest` inside an interactive Dev Container.
## 
## \usage From `nwm-rte` repository root:
## ./.devcontainer/pytest/run_pytest_external.sh
## 
## \note
## Uses OS env var TARGET_IMAGE_NAME if it is set, otherwise default to "ngen_rte_ghcr".
## 

IMAGE=${TARGET_IMAGE_NAME:-"ngen_rte_ghcr"}
WORKDIR="/ngen-app/rte-pytest"

sudo docker run --entrypoint "/ngen-app/ngen-python/bin/python" \
    -w "${WORKDIR}" \
    -v "$(pwd)/:${WORKDIR}" \
    -v "$(pwd)/bin_mounted/:/ngen-app/bin/bin_mounted" \
    -v "$(pwd)/bin_mounted/test_data/s3/:${MNT__S3_DATA__CONTAINER_1}" \
    -v "$(pwd)/../ngen-forcing/:${MNT__NGEN_FORCING__CONTAINER_1}" \
    -v "$(pwd)/../nwm-msw-mgr/src/mswm/module_parameter_files/:${MNT__MODULE_PARAM_FILES_DIR__CONTAINER_1}" \
    -v "$(pwd)/../run_ngen/:${MNT__RUN_NGEN__CONTAINER_1}" \
    --rm ${IMAGE} -m pytest
