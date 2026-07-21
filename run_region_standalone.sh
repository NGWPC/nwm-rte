#!/bin/bash

set -euo pipefail
source config.bashrc
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

# sudo rm -rf ~/ngwpc/run_ngen/regionalization/test_bmi/${TEST_GAGE}

TEST_FORM_ASSIGN_GAGE="${INSTALLED_REGIONALIZATION_RESULTS}/${TEST_GAGE}/formulation_assignment.csv"
TEST_CAT_GRP_GAGE="${INSTALLED_REGIONALIZATION_RESULTS}/${TEST_GAGE}/catchment_groups.csv"

TEST_FORM_ASSIGN_VPU="${INSTALLED_REGIONALIZATION_RESULTS}/${TEST_VPU}/formulation_assignment.csv"
TEST_CAT_GRP_VPU="${INSTALLED_REGIONALIZATION_RESULTS}/${TEST_VPU}/catchment_groups.csv"

# Short Range
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "region_sr"
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "region_sr" --output_format CSV NetCDF

# Short Range VPU
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_VPU}" -cgf "${TEST_CAT_GRP_VPU}" -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "region_sr" -v "03S"

# Short Range with NWM Output Variables
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "region_sr_nwm_output" -nwmout
# Analysis & Assimilation
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "standard_ana" -dt "2026-03-30 06:00:00" -rname "region_ana"
# Analysis & Assimilation VPU
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_VPU}" -cgf "${TEST_CAT_GRP_VPU}" -fconfig "standard_ana" -dt "2026-03-30 06:00:00" -rname "region_ana" -v "03S"
# Medium Range
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "medium_range_blend" -dt "2026-03-30 06:00:00" -rname "region_mr"

# Medium Range Lagged Ensemble
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "no_da" "" ""
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem1" "" ""
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem2" "" ""
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem3" "" ""
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem4" "" ""
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem5" "" ""
# docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "medium_range" -dt "2026-03-30 06:00:00" -rname "region_mr_le" -le "mem6" "" ""

# Historical / Retrospective Forcing
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "aorc" -dt "2013-07-25 00:00:00" -dur 2 -rname "region_aorc"

# State saving and loading
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "standard_ana" -dt "2026-03-30 06:00:00" -rname "region_ana" --save_state --save_state_dir "/ngwpc/run_ngen/regionalization/region_ana/${TEST_GAGE}/state_save_dir/"
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "region_sr" --load_state_from "/ngwpc/run_ngen/regionalization/regiona_ana/${TEST_GAGE}/state_save/"

# Checkpoint restart
docker_run python -um "ngen_rte.run_regionalization_standalone" -n 2 -faf "${TEST_FORM_ASSIGN_GAGE}" -cgf "${TEST_CAT_GRP_GAGE}" -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "region_sr" --checkpoint_interval 3 --checkpoint_dir "/ngwpc/run_ngen/regionalization/region_sr/${TEST_GAGE}/checkpoint_dir/" -nwmout --output_format NetCDF
docker_run python -um "ngen_rte.run_restart" -src "/ngwpc/run_ngen/regionalization/region_sr/${TEST_GAGE}/" -dst "/ngwpc/run_ngen/regionalization/region_sr_restart/${TEST_GAGE}/" --checkpoint_dir "/ngwpc/run_ngen/regionalization/region_sr/${TEST_GAGE}/checkpoint_dir/"

exit 0
