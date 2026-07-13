#!/bin/bash

set -euo pipefail
source config.bashrc

## 
## \brief
## Download input data for one gage.
## 
## \desc
## Download input hydrofabric data from S3 and from APIs, for one USGS gage.
## Not needed for the "default" gage at the "default" realization, since those inputs are included in the repository.
## Downloads all vintages of hydrofabric associated with one gage ID.
##
## Uses various OS env vars from `config.bashrc`.
## 
## Has 3 positional arguments and 0 named arguments.
## 
## \option GAGE_ID
## The USGS gage ID to be downloaded, e.g. `"01121330"`
## 
## \option DOMAIN
## The domain that the gage ID resides in, e.g. `"CONUS"`
## 
## \option EDFS_API_ENVIRONMENT
## For EDFS API URL for nwm-rte setup scripts. Used to construct URL subdomain. Not used during ngen runtime. See -e, --environment in the ngen runtime CLI scripts.
## Default: 'test'. Choices: ['test', 'oe'].
## 
## \usage ./setup_data_one_gage.sh "01121330" "CONUS" "test"
## 

GAGE_ID="$1"
DOMAIN="$2"
EDFS_API_ENVIRONMENT="$3"

SRC_URL_STREAMFLOW_OBS="http://edfs.${EDFS_API_ENVIRONMENT}.nextgenwaterprediction.com/api/${EDFS_API_VERSION}/streamflow_observations/${GAGE_ID}/csv"

TGT_DIR_OBS_FLOW="${RUN_NGEN_ROOT__HOST}/data/streamflow_observations/${DOMAIN}/edfs_api_${EDFS_API_VERSION}"
TGT_FILE_OBS_FLOW="${TGT_DIR_OBS_FLOW}/${GAGE_ID}_hourly_discharge.csv"
SRC_FILE_NWM_RETRO="${SOURCE_BUCKET_DEV}/${SOURCE_PREFIX_ROOT}/nwm_retrospective/${GAGE_ID}.csv"

s3_copy "${SRC_FILE_NWM_RETRO}" "${RUN_NGEN_ROOT__HOST}/data/nwm_retrospective/"

mkdir_p "${TGT_DIR_OBS_FLOW}"
info "Downloading: ${SRC_URL_STREAMFLOW_OBS} -> ${TGT_FILE_OBS_FLOW}"
curl -f -o "${TGT_FILE_OBS_FLOW}" "${SRC_URL_STREAMFLOW_OBS}"  # Get from EDFS server

info "Listing available observed flow files on disk for provided gage: ${GAGE_ID}"
ls -1 "${TGT_DIR_OBS_FLOW}/" | grep ${GAGE_ID}


set -x
exit 0
