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

# sudo rm -rf ~/ngwpc/run_ngen/default/test_bmi/01123000


# Short Range
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr"
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr" -g "12175500"
# Short Range with NWM Output Variables
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr_nwm_output" -nwmout
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

# Historical / Retrospective Forcing
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "aorc" -dt "2013-07-25 00:00:00" -dur 2 -rname "default_aorc"
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "aorc" -dt "2013-07-25 00:00:00" -dur 2 -rname "default_aorc" -mf "snow-17,noah-owp-modular,smp,lasam,t-route" -rz "true"

# State saving and loading
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "standard_ana" -dt "2026-03-30 06:00:00" -rname "default_ana" --save_state
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr" --load_state_from /ngwpc/run_ngen/default/test_bmi/01123000/state_save/

# TEST_HYDROFAB_FILE="/s3/ngwpc-dev/rte-test-data/gages/gauge_01123000.gpkg"
# docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "aorc" -dt "2013-07-25 00:00:00" -dur 2 -rname "default_aorc" --hydrofab_file "${TEST_HYDROFAB_FILE}"

# Checkpoint restart
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr" --checkpoint_interval 3
docker_run python -um "ngen_rte.run_restart" -src "/ngwpc/run_ngen/default/test_bmi/01123000/" -dst "/ngwpc/run_ngen/default/test_bmi_restart/01123000/"

exit 0
