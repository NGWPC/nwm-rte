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

REFERENCE_GRID="/ngwpc/run_ngen/output_postprocess/nwm_output/analysis_assim/nwm.t00z.analysis_assim.land.tm00.conus.nc"
NETCDF_FOLDER="/ngwpc/run_ngen/output_postprocess/"
OUTPUT_FOLDER="/ngwpc/run_ngen/output_postprocess/"

docker_run python -um "ngen_rte.run_output_postprocess" -ncout "${NGEN_NETCDF_OUTPUT_FILE}" -gpkg "${NGEN_GPKG_FILE}" -ncf "${NETCDF_OUTPUT_FOLDER}" -tout "${TROUTE_OUTPUT_FILE}" -tlout "${TROUTE_LAKEOUTFILE}"

exit 0
