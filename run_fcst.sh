#!/bin/bash

set -euo pipefail

source run.sh

# Default to fcst_run1, override via CLI arg
fcst_run_name=${1:-"fcst_run1"}

set -x


# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" --help

# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -csdt "2025-09-12 00:00:00" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_cs_short" -fconfig short_range

docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_short" -fconfig short_range
# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_short_n2" -fconfig short_range -n 2

# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_ana" -fconfig standard_ana

### Medium Range
# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr" -fconfig medium_range_no_da

### Medium Range Lagged Ensemble Members
# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "no_da" "" ""
# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem1" "" ""
# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem2" "" ""
# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem3" "" ""
# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem4" "" ""
# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem5" "" ""
# docker_run python "/ngen-app/bin/bin_mounted/run_forecast.py" -n 2 -dt "2025-09-15 00:00:00" -rname "${fcst_run_name}_mr_le" -fconfig medium_range -le "mem6" "" ""

exit 0
