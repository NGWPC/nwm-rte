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
#docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -mf "snow-17,noah-owp-modular,smp,lasam,t-route" -rz "true"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -mf "snow-17,noah-owp-modular,smp,lasam,t-route" -rz "true" --gage_id "12175500"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm"

# TEST_HYDROFAB_FILE="/s3/ngwpc-dev/rte-test-data/gages/gauge_01123000.gpkg"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" --hydrofab_file "${TEST_HYDROFAB_FILE}"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -gdomain "Hawaii" --gage_id "16010000"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Hawaii" --gage_id "16010000"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -gdomain "Hawaii" --gage_id "16019000"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Hawaii" --gage_id "16019000"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -gdomain "Hawaii" --gage_id "16060000"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Hawaii" --gage_id "16060000"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -gdomain "Puerto_Rico" --gage_id "50014800"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Puerto_Rico" --gage_id "50014800"

# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "aorc" -gdomain "Alaska" --gage_id "15209700"
# docker_run python "/ngen-app/bin/bin_mounted/run_calibration.py" -n 2 -fsrc "nwm" -gdomain "Alaska" --gage_id "15209700"



exit 0
