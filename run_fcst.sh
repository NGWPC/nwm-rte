#!/bin/bash

set -euo pipefail
source run.sh

## 
## \brief
## Example commands for running "forecast" realizations.  See CLI args for [`run_forecast.py`](python_cli_help__run_forecast.py.txt).
## 
## \desc
## Source `./run.sh` to call its `docker_run` command for running "forecast" realizations.  It requires that the ngen runtime environment image has already been built using `./ngen_rte_build.sh`.
## 
## Various OS env vars are applied from `config.bashrc`. Notably `TARGET_IMAGE_NAME` is the image that is sourced (must have already been built) and launched as a container. Various data mount paths are also applied from `config.bashrc`.
## 
## <u>Requirements:</u>
## 
## The `ngen` runtime environment image (defined by `TARGET_IMAGE_NAME`) has already been built.
## 
## The various repositories and input data needed to run are available and mountable (see `./setup_clone_repos.sh`, `./setup_data.sh`, `./setup_data_one_gage.sh`).
## 
## A "calibration" realization has already been ran for the gage of interest, and its output is available at the expected location.
## 
## This script has 1 positional arguments and 0 named arguments.
## 
## \option fcst_run_name
## Optional. Default=`"fcst_run"`. Specify to choose the name of the forecast run.
## 
## \usage ./run_fcst.sh
## 

# Default to fcst_run1, override via CLI arg
fcst_run_name=${1:-"fcst_run1"}

set -x


# docker_run python -um "ngen_rte.run_forecast" --help

# State saving and loading
# docker_run python -um "ngen_rte.run_forecast" -csdt "2025-09-12 00:00:00" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_cs_short" -fconfig short_range --save_state
# docker_run python -um "ngen_rte.run_forecast" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_short" -fconfig short_range --load_state_from /ngwpc/run_ngen/kge_dds/test_bmi/01123000/Output/Model_State_Run/Cold_Start_Run/fcst_run1_cs_short/state_save/

docker_run python -um "ngen_rte.run_forecast" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_short" -fconfig short_range
# docker_run python -um "ngen_rte.run_forecast" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_short_n2" -fconfig short_range -n 2
# docker_run python -um "ngen_rte.run_forecast" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_short_n2_nwm_output" -fconfig short_range -n 2 -nwmout --output_format CSV NetCDF


# docker_run python -um "ngen_rte.run_forecast" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_ana" -fconfig standard_ana

# Medium Range
# docker_run python -um "ngen_rte.run_forecast" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr" -fconfig medium_range_no_da

# Medium Range Lagged Ensemble Members
# docker_run python -um "ngen_rte.run_forecast" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "no_da" "" ""
# docker_run python -um "ngen_rte.run_forecast" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem1" "" ""
# docker_run python -um "ngen_rte.run_forecast" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem2" "" ""
# docker_run python -um "ngen_rte.run_forecast" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem3" "" ""
# docker_run python -um "ngen_rte.run_forecast" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem4" "" ""
# docker_run python -um "ngen_rte.run_forecast" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem5" "" ""
# docker_run python -um "ngen_rte.run_forecast" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem6" "" ""

exit 0
