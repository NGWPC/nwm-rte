#!/bin/bash

set -euo pipefail

source run.sh
set -x


docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" --help
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -fregion "Hawaii" --gage_id__gage_vintage "16010000" "2025_Apr_07_21_40_35"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -fregion "Hawaii" --gage_id__gage_vintage "16019000" "2025_Jul_15_16_33_40"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -fregion "Hawaii" --gage_id__gage_vintage "16060000" "2025_Apr_07_21_41_09"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -fregion "Puerto_Rico" --gage_id__gage_vintage "50014800" "2025_Apr_08_15_13_08"


exit 0
