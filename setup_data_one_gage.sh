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
## Has 2 positional arguments and 0 named arguments.
## 
## \option GAGE_ID
## The USGS gage ID to be downloaded, e.g. `"01121330"`
## 
## \option DOMAIN
## The domain that the gage ID resides in, e.g. `"CONUS"`
## 
## \usage ./setup_data_one_gage.sh "01121330" "CONUS"
## 

GAGE_ID="$1"
DOMAIN="$2"

EDFS_API_VERSION=v1

SRC_BUCKET_HYDROFABRIC="ngwpc-hydrofabric"
SRC_BUCKET_DEV="ngwpc-dev"
SRC_URL_STREAMFLOW_OBS="http://edfs.test.nextgenwaterprediction.com/api/${EDFS_API_VERSION}/streamflow_observations/${GAGE_ID}/csv"

SRC_PREFIX_2p2_GPKG="${SRC_BUCKET_HYDROFABRIC}/2.2/${DOMAIN}/${GAGE_ID}/GEOPACKAGE/USGS"
TGT_DIR_2p2_GPKG="${S3_ROOT__HOST}/${SRC_PREFIX_2p2_GPKG}"

# SRC_PREFIX_2p1_OBS_FLOW="${SRC_BUCKET_HYDROFABRIC}/2.1/${DOMAIN}/${GAGE_ID}/OBSERVATIONAL/USGS"  # s3 source replaced by EDFS server
TGT_DIR_OBS_FLOW="${RUN_NGEN_ROOT__HOST}/data/streamflow_observations/${DOMAIN}/edfs_api_${EDFS_API_VERSION}"
TGT_FILE_OBS_FLOW="${TGT_DIR_OBS_FLOW}/${GAGE_ID}_hourly_discharge.csv"
SRC_FILE_NWM_RETRO="${SRC_BUCKET_DEV}/ngen-static-files/nwm_retrospective/${GAGE_ID}.csv"
TGT_DIR_NWM_RETRO="${S3_ROOT__HOST}/$(dirname "$SRC_FILE_NWM_RETRO")"


function s3_test_exists() {
    echo "Testing if exists: s3://${1}"
    aws s3 ls s3://${1} > /dev/null || fatal "Does not exist: s3://${1}"
}

function s3_sync() {
    echo "Syncing s3://${1}/ -> ${2}/"
    aws s3 sync "s3://${1}/" "${2}/"
}

function s3_copy() {
    echo "Copying s3://${1} -> ${2}"
    aws s3 cp "s3://${1}" "${2}"
}

s3_test_exists "${SRC_PREFIX_2p2_GPKG}"
# s3_test_exists "${SRC_PREFIX_2p1_OBS_FLOW}"  # s3 source replaced by EDFS server
s3_test_exists "${SRC_FILE_NWM_RETRO}"

s3_sync "${SRC_PREFIX_2p2_GPKG}" "${TGT_DIR_2p2_GPKG}"
# s3_sync "${SRC_PREFIX_2p1_OBS_FLOW}" "${TGT_DIR_OBS_FLOW}"  # s3 source replaced by EDFS server

s3_copy "${SRC_FILE_NWM_RETRO}" "${TGT_DIR_NWM_RETRO}/"

# echo "Downloading: ${SRC_URL_STREAMFLOW_OBS} -> ${TGT_FILE_OBS_FLOW}"
# mkdir -p "${TGT_DIR_OBS_FLOW}"
# curl -f -o "${TGT_FILE_OBS_FLOW}" "${SRC_URL_STREAMFLOW_OBS}"  # Get from EDFS server

echo "Listing available gpkg vintages after sync for provided gage: ${GAGE_ID}"
ls -1 "${TGT_DIR_2p2_GPKG}/"

echo "Listing available observed flow files on disk for provided gage: ${GAGE_ID}"
ls -1 "${TGT_DIR_OBS_FLOW}/" | grep ${GAGE_ID}


set -x
exit 0
