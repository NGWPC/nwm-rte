#!/bin/bash

set -euo pipefail

source config.bashrc

## 
## \brief
## Runs an ephemeral docker container to execute `python -m pytest` and quit. An alternative to running `pytest` inside an interactive Dev Container.
## 
## \usage From `nwm-rte` repository root:
## ./run_pytest_external.sh
## 
## \note
## Uses OS env var TARGET_IMAGE_NAME if it is set, otherwise default to "ngen_rte_ghcr".
## 

IMAGE=${TARGET_IMAGE_NAME:-"ngen_rte_ghcr"}

sudo docker run --entrypoint "/ngen-app/ngen-python/bin/python" \
    -w "/ngen-app/bin/bin_mounted/" \
    -v "$(pwd)/bin_mounted/:/ngen-app/bin/bin_mounted" \
    -v "$(pwd)/bin_mounted/ngen_rte/tests/test_data/s3/:${MNT__S3_DATA__CONTAINER}" \
    -v "$(pwd)/../run_ngen/:${MNT__RUN_NGEN__CONTAINER}" \
    --rm ${IMAGE} -m pytest
