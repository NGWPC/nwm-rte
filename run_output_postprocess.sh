#!/bin/bash

set -euo pipefail
source run.sh
set -x

## 
## \brief
## Example commands for running the "output_postprocess" (overall_netcdf_workflow)..  See CLI args for [`run_output_process.py`](python_cli_help__run_output_postprcoss.py.txt).
## 
## \desc
## Source `./run.sh` to call its `docker_run` command for running NetCDF output postprocess workflows.  It requires that the ngen runtime environment image has already been built using `./ngen_rte_build.sh`.
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
## \usage ./run_output_postprocess.sh
## 

NGEN_NETCDF_OUTPUT_FILE="/ngwpc/run_ngen/default/default_sr/03S/Output/catchment_output.nc"
NGEN_GPKG_FILE="/ngwpc/run_ngen/default/default_sr/03S/Input/vpu_03S.gpkg"
OUTPUT_FOLDER="/ngwpc/run_ngen/output_postprocess/"
TROUTE_OUTPUT_FILE="/ngwpc/run_ngen/default/default_sr/03S/Output/troute_output.nc"
TROUTE_LAKEOUT_FILE="/ngwpc/run_ngen/default/default_sr/03S/Output/troute_lakeout.nc"

docker_run python -um "ngen_rte.run_output_postprocess" -ncout "${NGEN_NETCDF_OUTPUT_FILE}" -gpkg "${NGEN_GPKG_FILE}" -of "${NETCDF_OUTPUT_FOLDER}" -tout "${TROUTE_OUTPUT_FILE}" -tlout "${TROUTE_LAKEOUTFILE}"

exit 0
