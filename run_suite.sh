#!/bin/bash

set -euo pipefail
source run.sh
set -x

## 
## \brief
## Example commands for running realizations of various types.
## See CLI args for [`run_forecast.py`](python_cli_help__run_forecast.py.txt), [`run_default.py`](python_cli_help__run_default.py.txt), [`run_calibration.py`](python_cli_help__run_calibration.py.txt), and [`run_tests.py`](python_cli_help__run_tests.py.txt).
## 
## \desc
## Source `./run.sh` to call its `docker_run` command for running realizations of various types ("default", "calibration", and "forecast").  It requires that the ngen runtime environment image has already been built using `./ngen_rte_build.sh`.
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
## \usage ./run_suite.sh
## 

# CONUS NWM calibration using a short duration
# sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/01123000
docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "nwm" -start "2013-07-25 00:00:00" -dur 2

# CONUS AORC calibration using a long duration
# sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/01123000
docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "aorc" -start "2013-07-01 00:00:00" -dur 120

# CONUS forecasts: short range, analysis & assimilation, and medium range
docker_run python -um "ngen_rte.run_forecast" -fconfig "short_range" -dt "2025-07-10 04:00:00" -rname "fcst_run1_short_range"
# docker_run python -um "ngen_rte.run_forecast" -fconfig "short_range" -dt "2025-07-10 04:00:00" -rname "fcst_run1_short_range_n2" -n 2
docker_run python -um "ngen_rte.run_forecast" -fconfig "standard_ana" -dt "2025-07-10 10:00:00" -rname "fcst_run1_standard_ana"
docker_run python -um "ngen_rte.run_forecast" -fconfig "medium_range_blend" -dt "2025-07-10 00:00:00" -rname "fcst_run1_medium_range_blend"

# PR sample calibration during Hurricane Maria
# sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/50027000
docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "nwm" -gdomain "Puerto_Rico" --gage_id "50027000" -start "2017-09-20 00:00:00" -dur 4

# Hawaii sample calibration during Tropical Storm Fabio
# sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/16060000
docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "nwm" -gdomain "Hawaii" --gage_id "16060000" -start "2006-08-06 00:00:00" -dur 2

# Alaksa sample calibration 
# sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/15209700
docker_run python -um "ngen_rte.run_calibration" -n 2 -fconfig "nwm" -gdomain "Alaska" --gage_id "15209700" -start "2016-07-25 00:00:00" -dur 2

# Initialize many forecast types in series, stopping them after a duration without waiting for completion
docker_run python -um "ngen_rte.tests.run_tests" --do_all_forcing_configs --fcst_run_name "test_all" --quit_forecast_after_duration 120

## CONUS forecasts: short range, analysis & assimilation, and medium range
#docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -fconfig "short_range" -dt "2025-07-10 04:00:00" -rname "fcst_run1_short_range"
#docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -fconfig "standard_ana" -dt "2025-07-10 10:00:00" -rname "fcst_run1_standard_ana"
#docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -fconfig "medium_range_blend" -dt "2025-07-10 00:00:00" -rname "fcst_run1_medium_range_blend"
#
## PR sample calibration during Hurricane Maria
#sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/50027000
#docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Puerto_Rico" --gage_id__gage_vintage "50027000" "2025_Apr_08_15_37_58" -start "2017-09-20 00:00:00" -dur 4
#
## Hawaii sample calibration during Tropical Storm Fabio
#sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/16060000
#docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Hawaii" --gage_id__gage_vintage "16060000" "2025_Apr_07_21_41_09" -start "2006-08-06 00:00:00" -dur 2
#
## Alaksa sample calibration 
#sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/15209700
#docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Alaska" --gage_id__gage_vintage "15209700" "2025_Mar_14_21_20_29" -start "2016-07-25 00:00:00" -dur 2
#
## Initialize many forecast types in series, stopping them after a duration without waiting for completion
#docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_all_forcing_configs --fcst_run_name "test_all" --quit_forecast_after_duration 120
#
exit 0
