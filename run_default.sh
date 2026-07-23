#!/bin/bash

set -euo pipefail
source run.sh
set -x

## 
## \brief
## Example commands for running "default" realizations.  See CLI args for [`run_default.py`](python_cli_help__run_default.py.txt).
## 
## \desc
## Source `./run.sh` to call its `docker_run` command for running "default" realizations.  It requires that the ngen runtime environment image has already been built using `./ngen_rte_build.sh`.
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
## \usage ./run_default.sh
## 

# sudo rm -rf ~/ngwpc/run_ngen/default/test_bmi/${TEST_GAGE}


# 7 day Cold Start
docker_run python -um "ngen_rte.run_default" -n 2 -csdt "2023-12-10 00:00:00" -dt "2023-12-17 00:00:00" -rname "default_ana_7day" -fconfig short_range --save_state -v "01" --output_format NetCDF

# 1 day Intermediate AnAs
docker_run python -um "ngen_rte.run_default" -n 2 -csdt "2023-12-17 00:00:00" -dt "2023-12-18 00:00:00" -rname "default_ana_-2d_-1d" -fconfig short_range --save_state --load_state_from /ngwpc/run_ngen/default/default_ana_7day/01123000/state_save/ -v "01" --output_format NetCDF
docker_run python -um "ngen_rte.run_default" -n 2 -csdt "2023-12-18 00:00:00" -dt "2023-12-19 00:00:00" -rname "default_ana_-1d_0d" -fconfig short_range --save_state --load_state_from /ngwpc/run_ngen/default/default_ana_-2d_-1d/01123000/state_save/ -v "01" --output_format NetCDF 
docker_run python -um "ngen_rte.run_default" -n 2 -csdt "2023-12-19 00:00:00" -dt "2023-12-20 00:00:00" -rname "default_ana_0d_1d" -fconfig short_range --save_state --load_state_from /ngwpc/run_ngen/default/default_ana_-1d_0d/01123000/state_save/ -v "01" --output_format NetCDF
docker_run python -um "ngen_rte.run_default" -n 2 -csdt "2023-12-20 00:00:00" -dt "2023-12-21 00:00:00" -rname "default_ana_1d_2d" -fconfig short_range --save_state --load_state_from /ngwpc/run_ngen/default/default_ana_0d_1d/01123000/state_save/ -v "01" --output_format NetCDF

# 5 Short Range
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2023-12-17 00:00:00" -rname "default_sr_-2d" --load_state_from /ngwpc/run_ngen/default/default_ana_7day/01123000/state_save/ -v "01" --output_format NetCDF
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2023-12-18 00:00:00" -rname "default_sr_-1d" --load_state_from /ngwpc/run_ngen/default/default_ana_-2d_-1d/01123000/state_save/ -v "01" --output_format NetCDF
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2023-12-19 00:00:00" -rname "default_sr_0d" --load_state_from /ngwpc/run_ngen/default/default_ana_-1d_0d/01123000/state_save/ -v "01" --output_format NetCDF
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2023-12-20 00:00:00" -rname "default_sr_1d" --load_state_from /ngwpc/run_ngen/default/default_ana_0d_1d/01123000/state_save/ -v "01" --output_format NetCDF
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2023-12-21 00:00:00" -rname "default_sr_2d" --load_state_from /ngwpc/run_ngen/default/default_ana_1d_2d/01123000/state_save/ -v "01" --output_format NetCDF

exit 0
