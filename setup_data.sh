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

# Download regionalization data
# Check if --regionalization or -r flag (argument) is passed
if [[ "$@" =~ (--regionalization|-r) ]]; then
    s3_sync "${SOURCE_BUCKET_DEV}/${SOURCE_PREFIX_ROOT}/regionalization/data/inputs" "${MNT__NWM_REGION_MGR__INPUT_DATA}"
fi

# Download test gage data using setup_data_one_gage.sh
./setup_data_one_gage.sh "${TEST_GAGE}" "${TEST_DOMAIN}" "${EDFS_API_ENVIRONMENT}"

# Download calibration parameterization files
s3_sync "${SOURCE_BUCKET_DEV}/${SOURCE_PREFIX_ROOT}/calib_params_tab_delimited" "${RUN_NGEN_ROOT__HOST}/data/calib_params_tab_delimited"

# Download ESMF mesh files for NWM forcing (CONUS and oCONUS)
s3_sync "${SOURCE_BUCKET_DEV}/${SOURCE_PREFIX_ROOT}/esmf/esmf_mesh" "${RUN_NGEN_ROOT__HOST}/data/esmf_mesh"

# Download RFC reservoir gage timeseries data
s3_sync "${SOURCE_BUCKET_DEV}/${SOURCE_PREFIX_ROOT}/rfc/reservoirs/timeseries" "${RUN_NGEN_ROOT__HOST}/data/rfc/reservoirs/timeseries"

set -x
exit 0
