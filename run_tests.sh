#!/bin/bash

set -euo pipefail

source run.sh

# Default to fcst_run1, override via CLI arg
fcst_run_name=${1:-"fcst_run1"}

set -x


# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --help
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --noop
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_calibration --fcst_run_name "${fcst_run_name}"
docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_calibration --skip_forecast --nprocs 2 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" --do_calibration --skip_forecast --nprocs 2 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" -g "01121330" "2025_Jan_30_13_08_20" --do_calibration --skip_forecast --nprocs 2 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" -g "01121330" "2025_Jan_30_13_08_20" --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" -g "02207385" "2025_Mar_14_21_15_07" --do_calibration --skip_forecast --nprocs 2 --fcst_run_name "${fcst_run_name}"
# docker_run python "/ngen-app/bin/bin_mounted/run_tests.py" -g "02207385" "2025_Mar_14_21_15_07" --fcst_run_name "${fcst_run_name}"
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

exit 0
