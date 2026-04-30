#!/bin/bash

set -euo pipefail
source config.bashrc
set -x

## 
## \brief
## Download various global input data, as well as specific input data for one example gage.
## 
## \desc
## Download input data from S3 and from APIs.  Not needed for the "default" gage at the "default" realization, since those inputs are included in the repository.
## Calls `./setup_data_one_gage.sh` for the default gage ID.
##
## Uses various OS env vars from `config.bashrc`.
## 
## Has 0 positional arguments and 1 named argument.
## 
## \option -r, --regionalization
## If provided, extra data will be downloaded for the regionalization workflow. Should be ran *after* cloning the `nwm-region-mgr` repository.
## 
## \usage ./setup_data.sh
## \usage ./setup_data.sh -r
## 

mkdir -p "${RUN_NGEN_ROOT__HOST}"
mkdir -p "${S3_ROOT__HOST}"

# Download regionalization data
# Check if --regionalization or -r flag (argument) is passed
if [[ "$@" =~ (--regionalization|-r) ]]; then
    aws s3 sync "s3://ngwpc-dev/regionalization/data/inputs/" "${MNT__NWM_REGION_MGR__INPUT_DATA}/"
    aws s3 sync "s3://ngwpc-dev/regionalization/data/inputs/ngen/module_parameter_files/" "${MNT__NWM_REGION_MGR__INPUT_DATA}/module_parameter_files/"
fi

# TODO if updating these, also need to update run_tests.py
TEST_GAGE="01123000"
DOMAIN="CONUS"
WORKFLOW_INPUT_CONFIG_ROOT="${RUN_NGEN_ROOT__HOST}/configs"

DATA__PARAMETERS__S3_SOURCE="s3://ngwpc-dev/rte-test-data/parameters"
DATA__PARAMETERS__HOST="${RUN_NGEN_ROOT__HOST}/data"

DATA__GEO_EM_CONUS_NC__S3_SOURCE="s3://ngwpc-dev/rte-test-data/esmf/geo_em_CONUS.nc"
DATA__GEO_EM_CONUS_NC__HOST="${RUN_NGEN_ROOT__HOST}/data/esmf_mesh/NWM/domain/geo_em_CONUS.nc"

TEST_RUN_CONFIG__CALIBRATION__SOURCE="s3://ngwpc-dev/rte-test-data/configs/input_calibration_bmi.config"
TEST_RUN_CONFIG__FORECAST__SOURCE="s3://ngwpc-dev/rte-test-data/configs/input_forecast.config"

# Download test gage data using setup_data_one_gage.sh
./setup_data_one_gage.sh "${TEST_GAGE}" "${DOMAIN}"
# Also download forcing data for the gage
aws s3 sync "s3://ngwpc-forcing/aorc_2.2/CONUS/Gage_${TEST_GAGE}/" "${S3_ROOT__HOST}/ngwpc-forcing/aorc_2.2/CONUS/Gage_${TEST_GAGE}/"

# Download various ngen parameterization files
aws s3 sync "${DATA__PARAMETERS__S3_SOURCE}/" "${DATA__PARAMETERS__HOST}/"
aws s3 cp "${DATA__GEO_EM_CONUS_NC__S3_SOURCE}" "${DATA__GEO_EM_CONUS_NC__HOST}"

# Download .config files
mkdir -p "${WORKFLOW_INPUT_CONFIG_ROOT}"

# Calibration config file
# curl -O --output-dir "${WORKFLOW_INPUT_CONFIG_ROOT}/" "https://raw.githubusercontent.com/NGWPC/nwm-msw-mgr/development/src/mswm/example_inputs/calibration/input_calibration.config"
aws s3 cp "${TEST_RUN_CONFIG__CALIBRATION__SOURCE}" "${WORKFLOW_INPUT_CONFIG_ROOT}/"

# Forecast config file
# curl -O --output-dir "${WORKFLOW_INPUT_CONFIG_ROOT}/" "https://raw.githubusercontent.com/NGWPC/nwm-msw-mgr/development/src/mswm/example_inputs/forecast/input_forecast.config"
aws s3 cp "${TEST_RUN_CONFIG__FORECAST__SOURCE}" "${WORKFLOW_INPUT_CONFIG_ROOT}/"

# Data for oCONUS NWM
aws s3 cp "s3://ngwpc-dev/kyle.larkin/esmf/geo_em_Alaska.nc" "${RUN_NGEN_ROOT__HOST}/data/esmf_mesh/NWM/domain/"
aws s3 cp "s3://ngwpc-dev/kyle.larkin/esmf/geo_em_Hawaii.nc" "${RUN_NGEN_ROOT__HOST}/data/esmf_mesh/NWM/domain/"
aws s3 cp "s3://ngwpc-dev/kyle.larkin/esmf/geo_em_PuertoRico.nc" "${RUN_NGEN_ROOT__HOST}/data/esmf_mesh/NWM/domain/geo_em_Puerto_Rico.nc"

aws s3 cp "s3://ngwpc-dev/rte-test-data/geogrid/GEOGRID_LDASOUT_Spatial_Metadata_AK.nc" "${RUN_NGEN_ROOT__HOST}/data/GEOGRID_LDASOUT_Spatial_Metadata_AK.nc"

exit 0
