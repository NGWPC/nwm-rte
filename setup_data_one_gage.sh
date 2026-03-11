#!/bin/bash
# 
# This downloads all hydrofabric geopackages (all vintages) associated with one USGS gage.
# 
# Usage:
#   Run from RTE repo root, providing gage ID as single argument, e.g.: ./setup_data_one_gage.sh "01121330" "CONUS"
# 


set -euo pipefail

source config.bashrc

GAGE_ID="$1"
DOMAIN="$2"

SRC_BUCKET_HYDROFABRIC="ngwpc-hydrofabric"
SRC_BUCKET_DEV="ngwpc-dev"

SRC_PREFIX_2p2_GPKG="${SRC_BUCKET_HYDROFABRIC}/2.2/${DOMAIN}/${GAGE_ID}/GEOPACKAGE/USGS"
TGT_DIR_2p2_GPKG="${S3_ROOT__HOST}/${SRC_PREFIX_2p2_GPKG}"

### For LSTM
SRC_PREFIX_2p1_OBS_FLOW="${SRC_BUCKET_HYDROFABRIC}/2.1/${DOMAIN}/${GAGE_ID}/OBSERVATIONAL/USGS"
TGT_DIR_2p1_OBS_FLOW="${S3_ROOT__HOST}/${SRC_PREFIX_2p1_OBS_FLOW}"
### For LSTM
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
### Needed only for LSTM
s3_test_exists "${SRC_PREFIX_2p1_OBS_FLOW}"
s3_test_exists "${SRC_FILE_NWM_RETRO}"

s3_sync "${SRC_PREFIX_2p2_GPKG}" "${TGT_DIR_2p2_GPKG}"
s3_sync "${SRC_PREFIX_2p1_OBS_FLOW}" "${TGT_DIR_2p1_OBS_FLOW}"
s3_copy "${SRC_FILE_NWM_RETRO}" "${TGT_DIR_NWM_RETRO}"

echo "Listing available gpkg vintages after sync for provided gage: ${GAGE_ID}"
ls -1 "${TGT_DIR_2p2_GPKG}/"

echo "Listing available 2.1 observed flow vintages after sync for provided gage: ${GAGE_ID}"
ls -1 "${TGT_DIR_2p1_OBS_FLOW}/"


set -x
exit 0
