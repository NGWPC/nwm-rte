#!/bin/bash

set -euo pipefail
source run.sh
set -x

## 
## \brief
## Example commands for running the "output_mosaic" workflow..  See CLI args for [`run_output_mosaic.py`](python_cli_help__run_output_mosaic.py.txt).
## 
## \desc
## Source `./run.sh` to call its `docker_run` command for running NetCDF output mosaicing workflows for combining gridded output files.  It requires that the ngen runtime environment image has already been built using `./ngen_rte_build.sh`.
## 
## Various OS env vars are applied from `config.bashrc`. Notably `TARGET_IMAGE_NAME` is the image that is sourced (must have already been built) and launched as a container. Various data mount paths are also applied from `config.bashrc`.
## 
## Has 0 positional arguments and 0 named arguments.
## 
## <u>Requirements:</u>
## 
## The `ngen` runtime environment image (defined by `TARGET_IMAGE_NAME`) has already been built.
## 
## The various repositories and input data needed to run are available and mountable (see `./setup_clone_repos.sh`, `./setup_data.sh`, `./setup_data_one_gage.sh`).
## 
## \usage ./run_output_mosaic.sh
## 

NETCDF_FOLDER="/ngwpc/run_ngen/output_postprocess/nwm_output/"
OUTPUT_FOLDER="/ngwpc/run_ngen/output_postprocess/mosaic/"
CONFIG_JSON_FILE="/ngwpc/run_ngen/output_postprocess/configs/metadata_config.json"
OUTPUT_CYCLE_HOUR=0
OUTPUT_CYCLE_TYPE="analysis_assim"
OUTPUT_CYCLE_DOMAIN="conus"

docker_run python -um "ngen_rte.run_output_mosaic" -ncf "${NETCDF_FOLDER}" -of "${OUTPUT_FOLDER}"\
    -cfg "${CONFIG_JSON_FILE}" -och "${OUTPUT_CYCLE_HOUR}" -oct "${OUTPUT_CYCLE_TYPE}" -ocd "${OUTPUT_CYCLE_DOMAIN}"

exit 0
