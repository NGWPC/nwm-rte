#!/bin/bash

set -euo pipefail
source run.sh

## 
## \brief
## Run a series of "forecast" realizations via `run_tests.py` with various forcing configurations, optionally with "calibration" realizations first.
## 
## \desc
## Source `./run.sh` to call its `docker_run` command for running `run_tests.py`.  It requires that the ngen runtime environment image has already been built using `./ngen_rte_build.sh`.
## 
## When realizations fail, this program does not halt, but rather moves to the next configuration type in the list, with the goal of "trying" many different realization configurations in one call.
## 
## The status of each configuration's build step and run step is reported and written to a json file at the end.
## 
## The Python script `run_tests.py` includes options for stopping realizations mid-way through their run, rather than waiting for them to complete.
## 
## Various OS env vars are applied from `config.bashrc`. Notably `TARGET_IMAGE_NAME` is the image that is sourced (must have already been built) and launched as a container. Various data mount paths are also applied from `config.bashrc`.
## 
## <u>Requirements:</u>
## 
## The `ngen` runtime environment image (defined by `TARGET_IMAGE_NAME`) has already been built.
## 
## The various repositories and input data needed to run are available and mountable (see `./setup_clone_repos.sh`, `./setup_data.sh`, `./setup_data_one_gage.sh`).
## 
## This script has 1 positional arguments and 0 named arguments.
## 
## \option fcst_run_name
## Optional. Default=`"fcst_run"`. Specify to choose the name of the forecast run.
## 
## \usage ./run_tests.sh
## 

# Default to fcst_run1, override via CLI arg
fcst_run_name=${1:-"fcst_run1"}

set -x


# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --help
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --noop
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_calibration --fcst_run_name "${fcst_run_name}"
docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_calibration --skip_forecast --nprocs 2 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_calibration --skip_forecast --nprocs 2 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" -g "01121330" --do_calibration --skip_forecast --nprocs 2 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" -g "01121330" --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" -g "02207385" --do_calibration --skip_forecast --nprocs 2 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" -g "02207385" --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_coldstart --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --quit_forecast_after_forcing_running --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --quit_forecast_after_duration 15 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --help --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_calibration --do_coldstart --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_all_forcing_configs --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_all_forcing_configs --quit_forecast_after_forcing_running --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_all_forcing_configs --quit_forecast_after_duration 15 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_calibration --do_coldstart --do_all_forcing_configs --fcst_run_name "${fcst_run_name}"

# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" -calfsrcs "aorc" -mff "/ngen-app/nwm-automation-scripts/model_formulations/formulations_munged_setup.tsv" -calib -nofcst -fcname "${fcst_run_name}_test_forms"
# docker_run python "/ngen-app/bin/bin_mounted/parse_test_results.py" -mff "/ngen-app/nwm-automation-scripts/model_formulations/formulations_munged_setup.tsv"

# TEST_HYDROFAB_FILE="/s3/ngwpc-dev/rte-test-data/gages/gauge_01123000.gpkg"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_calibration --skip_forecast --nprocs 2 --fcst_run_name "${fcst_run_name}" --hydrofab_file "${TEST_HYDROFAB_FILE}"

exit 0
