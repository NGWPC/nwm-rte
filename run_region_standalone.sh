#!/bin/bash

set -euo pipefail
source run.sh
set -x

## 
## \brief
## Example commands for running "regionalization" realizations.  See CLI args for [`run_regionalization_standalone.py`](python_cli_help__run_regionalization_standalone.py.txt).
## 
## \desc
## Source `./run.sh` to call its `docker_run` command for running "regionalization" realizations.  It requires that the ngen runtime environment image has already been built using `./ngen_rte_build.sh`.
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
## \usage ./run_region_standalone.sh
## 

# sudo rm -rf ~/ngwpc/run_ngen/regionalization/test_bmi/01123000

TEST_FORM_ASSIGN="/s3/ngwpc-dev/rte-test-data/regionalization/01123000/formulation_assignment.csv"
TEST_CAT_GRP="/s3/ngwpc-dev/rte-test-data/regionalization/01123000/catchment_groups.csv"

# Short Range
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "region_sr" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"

# # Short Range with NWM Output Variables
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "region_sr_nwm_output" -nwmout -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"
# # Analysis & Assimilation
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "standard_ana" -dt "2026-03-30 06:00:00" -rname "region_ana" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"
# # Medium Range
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "medium_range_blend" -dt "2026-03-30 06:00:00" -rname "region_mr" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"

# # Medium Range Lagged Ensemble
# # docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "no_da" "" "" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"
# # docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem1" "" "" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"
# # docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem2" "" "" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"
# # docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem3" "" "" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"
# # docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem4" "" "" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"
# # docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem5" "" "" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"
# # docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem6" "" "" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"

# # Historical / Retrospective Forcing
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "aorc" -dt "2013-07-25 00:00:00" -dur 2 -rname "region_aorc" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"

# # State saving and loading
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "standard_ana" -dt "2026-03-30 06:00:00" -rname "region_ana" --save_state -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "region_sr" --load_state_from /ngwpc/run_ngen/regionalization/test_bmi/01123000/state_save/ -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"

# # Checkpoint restart
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "region_sr" --checkpoint_interval 3 -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"
# docker_run python -um "ngen_rte.run_restart" -src "/ngwpc/run_ngen/regionalization/test_bmi/01123000/" -dst "/ngwpc/run_ngen/regionalization/test_bmi_restart/01123000/" -faf "${TEST_FORM_ASSIGN}" -cgf "${TEST_CAT_GRP}"

exit 0
