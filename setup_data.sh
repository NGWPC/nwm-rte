#!/bin/bash

set -euo pipefail
source config.bashrc

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
## Has 0 positional arguments and 2 named arguments.
## 
## \option -a, --api-environment
## For EDFS API URL for nwm-rte setup scripts. Used to construct URL subdomain. Not used during ngen runtime. See -e, --environment in the ngen runtime CLI scripts.
## Default: 'test'. Common choices: ['test', 'oe'].
## 
## \option -r, --regionalization
## If provided, extra data will be downloaded for the regionalization workflow. Should be ran *after* cloning the `nwm-region-mgr` repository.
## 
## \usage ./setup_data.sh
## \usage ./setup_data.sh -a 'oe'
## \usage ./setup_data.sh -a 'test' -r
## \usage ./setup_data.sh -a 'oe' -r
## 

# Parse named arg -a, --api-environment
if [[ "$@" =~ (--api-environment|-a)[[:space:]]+([^ ]+) ]]; then
    EDFS_API_ENVIRONMENT="${BASH_REMATCH[2]}"
else
    EDFS_API_ENVIRONMENT="test"
fi

mkdir_p "${RUN_NGEN_ROOT__HOST}"
mkdir_p "${S3_ROOT__HOST}"

# Download regionalization data
# Check if --regionalization or -r flag (argument) is passed
if [[ "$@" =~ (--regionalization|-r) ]]; then
    s3_sync "${SOURCE_BUCKET_DEV}/regionalization/data/inputs" "${MNT__NWM_REGION_MGR__INPUT_DATA}"
    s3_sync "${SOURCE_BUCKET_DEV}/regionalization/data/inputs/ngen/module_parameter_files" "${MNT__NWM_REGION_MGR__INPUT_DATA}/module_parameter_files"
fi

# NOTE if updating these, also need to update run_tests.py
TEST_GAGE="01123000"
TEST_DOMAIN="CONUS"
WORKFLOW_INPUT_CONFIG_ROOT="${RUN_NGEN_ROOT__HOST}/configs"

DATA__RTE_TEST__S3_SOURCE="${SOURCE_BUCKET_DEV}/rte-test-data"

DATA__ESMF_MESH_NWM_DIR__S3="${DATA__RTE_TEST__S3_SOURCE}/esmf/esmf_mesh/NWM/domain"
DATA__ESMF_MESH_NWM_DIR__HOST="${RUN_NGEN_ROOT__HOST}/data/esmf_mesh/NWM/domain"

DATA__PARAMETERS__S3_SOURCE="${DATA__RTE_TEST__S3_SOURCE}/parameters"
DATA__PARAMETERS__HOST="${RUN_NGEN_ROOT__HOST}/data"

TEST_RUN_CONFIG__CALIBRATION__SOURCE="${DATA__RTE_TEST__S3_SOURCE}/configs/input_calibration_bmi_nhf.config"
TEST_RUN_CONFIG__FORECAST__SOURCE="${DATA__RTE_TEST__S3_SOURCE}/configs/input_forecast_nhf.config"
TEST_RUN_HYDROFABRIC_NHF_GAGE__SOURCE="${DATA__RTE_TEST__S3_SOURCE}/gages/gauge_${TEST_GAGE}.gpkg"

TEST_RUN_REGIONALIZATION__SOURCE="${DATA__RTE_TEST__S3_SOURCE}/regionalization"
TEST_RUN_REGIONALIZATION__HOST="${RUN_NGEN_ROOT__HOST}/regionalization"

# Download test gage data using setup_data_one_gage.sh
./setup_data_one_gage.sh "${TEST_GAGE}" "${TEST_DOMAIN}" "${EDFS_API_ENVIRONMENT}"

# Download various ngen parameterization files
s3_sync "${DATA__PARAMETERS__S3_SOURCE}" "${DATA__PARAMETERS__HOST}"

# Download ESMF mesh files for NWM forcing (CONUS and oCONUS)
s3_sync "${DATA__ESMF_MESH_NWM_DIR__S3}" "${DATA__ESMF_MESH_NWM_DIR__HOST}"

# Download .config files
mkdir_p "${WORKFLOW_INPUT_CONFIG_ROOT}"

# Calibration config file
# curl -O --output-dir "${WORKFLOW_INPUT_CONFIG_ROOT}/" "https://raw.githubusercontent.com/NGWPC/nwm-msw-mgr/development/src/mswm/example_inputs/calibration/input_calibration.config"
s3_copy "${TEST_RUN_CONFIG__CALIBRATION__SOURCE}" "${WORKFLOW_INPUT_CONFIG_ROOT}/"

# Forecast config file
# curl -O --output-dir "${WORKFLOW_INPUT_CONFIG_ROOT}/" "https://raw.githubusercontent.com/NGWPC/nwm-msw-mgr/development/src/mswm/example_inputs/forecast/input_forecast.config"
s3_copy "${TEST_RUN_CONFIG__FORECAST__SOURCE}" "${WORKFLOW_INPUT_CONFIG_ROOT}/"

# Download gpkg for hydrofabric NHF test gage
s3_copy "${TEST_RUN_HYDROFABRIC_NHF_GAGE__SOURCE}" "${S3_ROOT__HOST}/ngwpc-dev/rte-test-data/gages/"

# Download test regionalization data
s3_sync "${TEST_RUN_REGIONALIZATION__SOURCE}" "${TEST_RUN_REGIONALIZATION__HOST}"


set -x
exit 0
