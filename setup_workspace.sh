#!/bin/bash

set -euo pipefail
set -x

source config.bashrc

mkdir -p "${REPOS_COMMON_ROOT__HOST}"
mkdir -p "${RUN_NGEN_ROOT__HOST}"
mkdir -p "${S3_ROOT__HOST}"


# TODO if updating these, also need to update example_workflow.py
TEST_GAGE="01123000"
WORKFLOW_INPUT_CONFIG_ROOT__COLDSTART="${RUN_NGEN_ROOT__HOST}/cold_start_workflow"
WORKFLOW_INPUT_CONFIG_ROOT__VALIDATION="${RUN_NGEN_ROOT__HOST}/kge_dds/test_bmi/${TEST_GAGE}/Output/Validation_Run"

DATA__HYDROFABRIC__S3_SOURCE="s3://ngwpc-hydrofabric"
DATA__HYDROFABRIC__HOST="${S3_ROOT__HOST}/ngwpc-hydrofabric"

DATA__PARAMETERS__S3_SOURCE="s3://ngwpc-dev/jeff.wade/rte_test_inputs"
DATA__PARAMETERS__HOST="${RUN_NGEN_ROOT__HOST}/data"

DATA__GEO_EM_CONUS_NC__S3_SOURCE="s3://ngwpc-dev/kyle.larkin/esmf/geo_em_CONUS.nc"
DATA__GEO_EM_CONUS_NC__HOST="${RUN_NGEN_ROOT__HOST}/data/geo_em_CONUS.nc"

DATA__GAGE_01011000_MESH_NC__S3_SOURCE="s3://ngwpc-dev/max.kipp/esmf_mesh/gages-01011000_ESMF_Mesh.nc"
DATA__GAGE_01011000_MESH_NC__S3_HOST="${RUN_NGEN_ROOT__HOST}/data/gages-01011000_ESMF_Mesh.nc"

TEST_RUN_CONFIG__CALIBRATION__SOURCE="s3://ngwpc-dev/max.kipp/run_ngen/cold_start_workflow/input_calibration_bmi.config"
TEST_RUN_CONFIG__FORECAST__SOURCE="s3://ngwpc-dev/max.kipp/run_ngen/cold_start_workflow/input_forecast.config"
TEST_RUN_CONFIG__VALIDATION__SOURCE="s3://ngwpc-dev/max.kipp/run_ngen/kge_dds/test_bmi/${TEST_GAGE}/Output/Validation_Run/${TEST_GAGE}_config_valid_best.yaml"


### Download hydrofabric data
mkdir -p "${DATA__HYDROFABRIC__HOST}"
aws s3 cp "${DATA__HYDROFABRIC__S3_SOURCE}/CFE-X_params_2.2.csv" "${DATA__HYDROFABRIC__HOST}/"
aws s3 cp "${DATA__HYDROFABRIC__S3_SOURCE}/deltat.csv" "${DATA__HYDROFABRIC__HOST}/"
aws s3 cp "${DATA__HYDROFABRIC__S3_SOURCE}/gpkg_hl_uri.tgz" "${DATA__HYDROFABRIC__HOST}/"
aws s3 cp "${DATA__HYDROFABRIC__S3_SOURCE}/hydrofabric_data.tgz" "${DATA__HYDROFABRIC__HOST}/"
aws s3 cp "${DATA__HYDROFABRIC__S3_SOURCE}/sac_sma_params_2.2.csv" "${DATA__HYDROFABRIC__HOST}/"
aws s3 cp "${DATA__HYDROFABRIC__S3_SOURCE}/snow17_params_2.2.csv" "${DATA__HYDROFABRIC__HOST}/"
aws s3 cp "${DATA__HYDROFABRIC__S3_SOURCE}/ueb_deltat_2.2.csv" "${DATA__HYDROFABRIC__HOST}/"

### Download test gage data
mkdir -p "${DATA__HYDROFABRIC__HOST}/2.2/CONUS/${TEST_GAGE}/GEOPACKAGE/USGS/2025_Mar_14_21_14_37"
aws s3 cp "${DATA__HYDROFABRIC__S3_SOURCE}/2.2/CONUS/${TEST_GAGE}/GEOPACKAGE/USGS/2025_Mar_14_21_14_37/gauge_${TEST_GAGE}.gpkg" "${DATA__HYDROFABRIC__HOST}/2.2/CONUS/${TEST_GAGE}/GEOPACKAGE/USGS/2025_Mar_14_21_14_37/"
aws s3 sync "s3://ngwpc-forcing/aorc_2.2/CONUS/Gage_${TEST_GAGE}/" "${S3_ROOT__HOST}/ngwpc-forcing/aorc_2.2/CONUS/Gage_${TEST_GAGE}/"

### Download various ngen parameterization files
aws s3 sync "${DATA__PARAMETERS__S3_SOURCE}/" "${DATA__PARAMETERS__HOST}/"
aws s3 cp "${DATA__GEO_EM_CONUS_NC__S3_SOURCE}" "${DATA__GEO_EM_CONUS_NC__HOST}"
aws s3 cp "${DATA__GAGE_01011000_MESH_NC__S3_SOURCE}" "${DATA__GAGE_01011000_MESH_NC__S3_HOST}"

### Download .config files
mkdir -p "${WORKFLOW_INPUT_CONFIG_ROOT__COLDSTART}"
## Calibration config file
# curl -O --output-dir "${WORKFLOW_INPUT_CONFIG_ROOT__COLDSTART}/" "https://raw.githubusercontent.com/NGWPC/nwm-msw-mgr/development/src/mswm/example_inputs/calibration/input_calibration.config"
aws s3 cp "${TEST_RUN_CONFIG__CALIBRATION__SOURCE}" "${WORKFLOW_INPUT_CONFIG_ROOT__COLDSTART}/"
## Forecast config file
# curl -O --output-dir "${WORKFLOW_INPUT_CONFIG_ROOT__COLDSTART}/" "https://raw.githubusercontent.com/NGWPC/nwm-msw-mgr/development/src/mswm/example_inputs/forecast/input_forecast.config"
aws s3 cp "${TEST_RUN_CONFIG__FORECAST__SOURCE}" "${WORKFLOW_INPUT_CONFIG_ROOT__COLDSTART}/"
# Validation config file
mkdir -p "${WORKFLOW_INPUT_CONFIG_ROOT__VALIDATION}"
aws s3 cp "${TEST_RUN_CONFIG__VALIDATION__SOURCE}" "${WORKFLOW_INPUT_CONFIG_ROOT__VALIDATION}/"

### Clone repos unless they already exist on disk
function clone_if_not_exists {
    if test -d "${REPOS_COMMON_ROOT__HOST}/${1}"; then
        info "Already exists: ${REPOS_COMMON_ROOT__HOST}/${1}"
    else
        ( cd "${REPOS_COMMON_ROOT__HOST}" && git clone --recurse-submodules "git@github.com:NGWPC/${1}.git" )
    fi
}
clone_if_not_exists "ngen-forcing"
clone_if_not_exists "ngen"
clone_if_not_exists "nwm-fcst-mgr"
clone_if_not_exists "nwm-msw-mgr"
clone_if_not_exists "nwm-cal-mgr"
clone_if_not_exists "nwm-verf"
clone_if_not_exists "nwm-eval-mgr"
clone_if_not_exists "nwm-region-mgr"
clone_if_not_exists "nwm-rte"
