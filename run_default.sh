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


# Short Range
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr"
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr" -g "12175500"
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr" -v "03S"

# Cold Start
docker_run python -um "ngen_rte.run_default" -n 2 -csdt "2025-09-14 00:00:00" -dt "2025-09-15 00:00:00" -rname "default_cs_short" -fconfig short_range --save_state

# Short Range with NWM Output Variables
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr_nwm_output" -nwmout --output_format CSV NetCDF
# Analysis & Assimilation
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "standard_ana" -dt "2026-03-30 06:00:00" -rname "default_ana"
# Medium Range
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "medium_range_blend" -dt "2026-03-30 06:00:00" -rname "default_mr"

# Medium Range Lagged Ensemble
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "default_mr_le" -le "no_da" "" ""
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "default_mr_le" -le "mem1" "" ""
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "default_mr_le" -le "mem2" "" ""
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "default_mr_le" -le "mem3" "" ""
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "default_mr_le" -le "mem4" "" ""
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "default_mr_le" -le "mem5" "" ""
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "default_mr_le" -le "mem6" "" ""

# # Historical / Retrospective Forcing
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "aorc" -dt "2013-07-25 00:00:00" -dur 2 -rname "default_aorc"
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "aorc" -dt "2013-07-25 00:00:00" -dur 2 -rname "default_aorc" -mf "snow-17,noah-owp-modular,smp,lasam,t-route" -rz "true"
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "aorc" -dt "2013-07-25 00:00:00" -dur 2 -rname "default_aorc" --output_format CSV NetCDF

# Reservoir RFC Data Assimilation (RFC reservoir test data only valid at "2026-07-13 12:00:00")
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-07-13 12:00:00" -rname "default_sr" -g "01205500" -rfc /ngwpc/run_ngen/data/rfc/reservoirs/timeseries/
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-07-13 12:00:00" -rname "default_sr_no_da" -g "01205500"

# State saving and loading
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "standard_ana" -dt "2026-03-30 06:00:00" -rname "default_ana" --save_state --save_state_dir /ngwpc/run_ngen/default/default_ana/${TEST_GAGE}/state_save_directory/
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "standard_ana" -dt "2026-03-30 06:00:00" -rname "default_ana" --save_state
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr" --load_state_from /ngwpc/run_ngen/default/test_bmi/${TEST_GAGE}/state_save/

docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "aorc" -dt "2013-07-25 00:00:00" -dur 2 -rname "default_aorc" --gage_id ${TEST_GAGE} --hydrofab_file "${TEST_HYDROFAB_FILE}"

# Checkpoint restart
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr" --checkpoint_interval 3 --checkpoint_dir "/ngwpc/run_ngen/default/default_sr/${TEST_GAGE}/checkpoint_directory/" -nwmout --output_format NetCDF
docker_run python -um "ngen_rte.run_restart" -src "/ngwpc/run_ngen/default/default_sr/${TEST_GAGE}/" -dst "/ngwpc/run_ngen/default/default_sr_restart/${TEST_GAGE}/" --checkpoint_dir "/ngwpc/run_ngen/default/default_sr/${TEST_GAGE}/checkpoint_directory/"

exit 0
