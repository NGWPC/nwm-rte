#!/bin/bash

set -euo pipefail

source run.sh
set -x

# CONUS NWM calibration using a short duration
sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/01123000
docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -start "2013-07-25 00:00:00" -dur 2

# CONUS AORC calibration using a long duration
sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/01123000
docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -start "2013-07-01 00:00:00" -dur 120

# CONUS forecasts: short range, analysis & assimilation, and medium range
docker_run python "/ngen-app/bin/bin_mounted/forecast_args_workflow.py" --skip_calibration -forcing_configuration "short_range" -cycle_datetime "2025-07-10 04:00:00" --fcst_run_name "fcst_run1_short_range"
docker_run python "/ngen-app/bin/bin_mounted/forecast_args_workflow.py" --skip_calibration -forcing_configuration "standard_ana" -cycle_datetime "2025-07-10 10:00:00" --fcst_run_name "fcst_run1_standard_ana"
docker_run python "/ngen-app/bin/bin_mounted/forecast_args_workflow.py" --skip_calibration -forcing_configuration "medium_range_blend" -cycle_datetime "2025-07-10 00:00:00" --fcst_run_name "fcst_run1_medium_range_blend"

# PR sample calibration during Hurricane Maria
sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/50027000
docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Puerto_Rico" --gage_id__gage_vintage "50027000" "2025_Apr_08_15_37_58" -start "2017-09-20 00:00:00" -dur 4

# Hawaii sample calibration during Tropical Storm Fabio
sudo rm -rf ~/ngwpc/run_ngen/kge_dds/test_bmi/16060000
docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Hawaii" --gage_id__gage_vintage "16060000" "2025_Apr_07_21_41_09" -start "2006-08-06 00:00:00" -dur 2

# Initialize many forecast types in series, stopping them after a duration without waiting for completion
docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_all_forcing_configs --fcst_run_name "test_all" --quit_forecast_after_duration 120

exit 0
