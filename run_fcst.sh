#!/bin/bash

set -euo pipefail

source run.sh

# Default to fcst_run1, override via CLI arg
fcst_run_name=${1:-"fcst_run1"}

set -x


# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" --help
docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -dt "2025-09-15 00:00:00" -csdt "2025-09-12 00:00:00" -rname "${fcst_run_name}"

exit 0
