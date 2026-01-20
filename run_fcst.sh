#!/bin/bash

set -euo pipefail

source run.sh

# Default to fcst_run1, override via CLI arg
fcst_run_name=${1:-"fcst_run1"}

set -x


docker_run python "/ngen-app/bin/bin_mounted/forecast_args_workflow.py" --help
# docker_run python "/ngen-app/bin/bin_mounted/forecast_args_workflow.py" -n 2 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/forecast_args_workflow.py" --skip_calibration -cycle_datetime "2025-09-15 00:00:00" --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/forecast_args_workflow.py" --skip_calibration -cycle_datetime "2025-09-15 00:00:00" -cold_start_datetime "2025-09-12 00:00:00" --fcst_run_name "${fcst_run_name}"


exit 0
