#!/bin/bash
# 
# This downloads all hydrofabric geopackages (all vintages) associated with one USGS gage.
# 
# Usage:
#   Run from RTE repo root, providing gage ID as single argument, e.g.: ./setup_data_one_gage.sh "01121330"
# 


set -euo pipefail

source config.bashrc

GAGE_ID="$1"

SRC_BUCKET="ngwpc-hydrofabric"
SRC_PREFIX="${SRC_BUCKET}/2.2/CONUS/${GAGE_ID}/GEOPACKAGE/USGS"
TGT_DIR="${S3_ROOT__HOST}/${SRC_PREFIX}"

echo "Testing if prefix exists: s3://${SRC_PREFIX}/"
aws s3 ls s3://${SRC_PREFIX}/ > /dev/null || fatal "Does not exist: s3://${SRC_PREFIX}/"

echo "Syncing s3://${SRC_PREFIX}/ -> ${TGT_DIR}/"
aws s3 sync "s3://${SRC_PREFIX}/" "${TGT_DIR}/"

echo "Listing available vintages after sync for provided gage: ${GAGE_ID}"
ls -1 "${TGT_DIR}/"

set -x
exit 0
