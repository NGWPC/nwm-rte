#!/bin/bash

set -euo pipefail
source run.sh
set -x

## 
## \brief
## Example commands for running "calibration" realizations.  See CLI args for [`run_calibration.py`](python_cli_help__run_calibration.py.txt).
## 
## \desc
## Source `./run.sh` to call its `docker_run` command for running "calibration" realizations.  It requires that the ngen runtime environment image has already been built using `./ngen_rte_build.sh`.
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
## \usage ./run_calib.sh
## 

# docker_run python -um "ngen_rte.run_calibration" --help

docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc"
# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc" --output_format CSV NetCDF
# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc" -mf "snow-17,noah-owp-modular,smp,lasam,t-route" -rz "true"
# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc" -mf "snow-17,noah-owp-modular,smp,lasam,t-route" -rz "true" --gage_id "12175500"
# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "nwm"


# TEST_HYDROFAB_FILE="/s3/ngwpc-dev/rte-test-data/gages/gauge_01123000.gpkg"
# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc" --gage_id 01123000 --hydrofab_file "${TEST_HYDROFAB_FILE}"

# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc" -gdomain "Hawaii" --gage_id "16010000"
# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "nwm" -gdomain "Hawaii" --gage_id "16010000"

# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc" -gdomain "Hawaii" --gage_id "16019000"
# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "nwm" -gdomain "Hawaii" --gage_id "16019000"

# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc" -gdomain "Hawaii" --gage_id "16060000"
# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "nwm" -gdomain "Hawaii" --gage_id "16060000"

# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc" -gdomain "Puerto_Rico" --gage_id "50014800"
# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "nwm" -gdomain "Puerto_Rico" --gage_id "50014800"

# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc" -gdomain "Alaska" --gage_id "15209700"
# docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "nwm" -gdomain "Alaska" --gage_id "15209700"



exit 0
