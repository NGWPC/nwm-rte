#!/bin/bash

set -euo pipefail
source run.sh
set -x

## 
## \brief
## Run "calibration" realizations.
## 
## \desc
## Source `./run.sh` to call its `docker_run` command for running "calibration" realizations.  It requires that the ngen runtime environment image has already been built using `./ngen_rte_build.sh`.
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
## \usage ./run_calib.sh
## 

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" --help

docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -gdomain "Hawaii" --gage_id__gage_vintage "16010000" "2025_Apr_07_21_40_35"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Hawaii" --gage_id__gage_vintage "16010000" "2025_Apr_07_21_40_35"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -gdomain "Hawaii" --gage_id__gage_vintage "16019000" "2025_Jul_15_16_33_40"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Hawaii" --gage_id__gage_vintage "16019000" "2025_Jul_15_16_33_40"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -gdomain "Hawaii" --gage_id__gage_vintage "16060000" "2025_Apr_07_21_41_09"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Hawaii" --gage_id__gage_vintage "16060000" "2025_Apr_07_21_41_09"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -gdomain "Puerto_Rico" --gage_id__gage_vintage "50014800" "2025_Apr_08_15_13_08"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Puerto_Rico" --gage_id__gage_vintage "50014800" "2025_Apr_08_15_13_08"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -gdomain "Alaska" --gage_id__gage_vintage "15209700" "2025_Mar_14_21_20_29"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Alaska" --gage_id__gage_vintage "15209700" "2025_Mar_14_21_20_29"

exit 0
