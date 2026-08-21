#!/bin/bash

set -euo pipefail
source config.bashrc

##
## \brief
## Download only the data needed to run a coastal forecast.
##
## \desc
## Unlike `setup_data.sh`, this does not download gage-specific streamflow
## data, calibration parameter tables, or RFC reservoir timeseries -- none
## of that is needed for a coastal forecast run. Downloads:
##
##   - ESMF mesh domain files (`GEOGRID_LDASOUT_Spatial_Metadata_*.nc` and
##     `geo_em_*.nc`) from `s3://ngwpc-coastal/parm/`, one region at a
##     time (`domain/` for CONUS, `domain_alaska/`, `domain_hawaii/`,
##     `domain_puertorico/`). Each region subdirectory also holds other,
##     unrelated files, so files are copied by exact name rather than
##     synced wholesale. The `GEOGRID_LDASOUT_Spatial_Metadata_*.nc` files
##     already use the same abbreviated region names in S3 as locally
##     (`AK`/`HI`/`PRVI`), but each region's `geo_em_*.nc` file is named
##     with the abbreviation in S3 (`geo_em_AK.nc`, `geo_em_HI.nc`,
##     `geo_em_PRVI.nc`) and renamed locally to the full region name
##     (`geo_em_Alaska.nc`, `geo_em_Hawaii.nc`, `geo_em_Puerto_Rico.nc`) to
##     match the existing local convention. This is a different bucket
##     than `setup_data.sh`'s `esmf/esmf_mesh` sync (that one is
##     intentionally not used here).
##   - Pre-computed ESMF regrid weights from
##     `s3://ngwpc-coastal/coastal_forecast_demo/regrid_weights/`, synced
##     into `data/esmf_mesh/regrid_weights/` -- this is the exact path
##     `ngen_rte.run_coastal` looks in/writes to at runtime (NOT the
##     top-level `data/regrid_weights/`, which is unused dead weight).
##     Pre-staging these avoids the (slow/memory-heavy) weight generation
##     step on first run.
##   - Regionalization input data (same as `setup_data.sh -r`). Should be
##     ran *after* cloning the `nwm-region-mgr` repository.
##   - The `run_coastal` working directory itself (`sfincs_models/` and
##     `schism_models/`), from
##     `s3://ngwpc-coastal/coastal_forecast_demo/run_coastal/`. This is
##     the `RUN_COASTAL_ROOT` sibling directory expected by
##     `nwm-coastal/ecflow_demo` (SCHISM/SFINCS working dir) -- it does
##     not exist yet on a fresh checkout, unlike `run_ngen`.
##
## Uses various OS env vars from `config.bashrc`.
##
## Has 0 positional arguments and 1 named argument.
##
## \option -s, --skip-existing
## If provided, skip re-downloading the named domain files (ESMF mesh
## `GEOGRID_LDASOUT_Spatial_Metadata_*.nc`/`geo_em_*.nc`) that already
## exist locally -- these are the large, slow ones. Synced directories
## (regrid weights, regionalization inputs, `run_coastal`) are always
## re-synced regardless of this flag; `aws s3 sync` already only
## transfers changed/missing objects within them. Omit this flag to
## always re-download the named domain files regardless of what's
## already on disk.
##
## \usage ./setup_data_coastal_forecast.sh
## \usage ./setup_data_coastal_forecast.sh -s
## \usage ./setup_data_coastal_forecast.sh --skip-existing
##

# Parse named arg -s, --skip-existing
if [[ "$@" =~ (--skip-existing|-s) ]]; then
    SKIP_EXISTING="true"
else
    SKIP_EXISTING="false"
fi

## \brief Copy a single S3 object to a local file path, honoring SKIP_EXISTING.
function s3_copy_maybe_skip () {
    local src="${1}"
    local dst="${2}"
    if [[ "${SKIP_EXISTING}" == "true" && -f "${dst}" ]]; then
        info "Skipping existing file (--skip-existing): ${dst}"
        return 0
    fi
    s3_copy "${src}" "${dst}"
}

## \env SOURCE_BUCKET_COASTAL Name of cloud bucket (no s3:// prefix), holding coastal-specific parm files.
SOURCE_BUCKET_COASTAL="ngwpc-coastal"
## \env SOURCE_PREFIX_COASTAL_PARM Prefix under SOURCE_BUCKET_COASTAL holding domain files.
SOURCE_PREFIX_COASTAL_PARM="parm"
## \env SOURCE_PREFIX_COASTAL_DEMO Prefix under SOURCE_BUCKET_COASTAL holding coastal forecast demo assets (e.g. pre-computed regrid weights).
SOURCE_PREFIX_COASTAL_DEMO="coastal_forecast_demo"

TGT_DIR_ESMF_DOMAIN="${RUN_NGEN_ROOT__HOST}/data/esmf_mesh/NWM/domain"
TGT_DIR_REGRID_WEIGHTS="${RUN_NGEN_ROOT__HOST}/data/esmf_mesh/regrid_weights"
## \env RUN_COASTAL_ROOT__HOST Root of the SCHISM/SFINCS working directory (sibling of `nwm-rte`, matching `RUN_COASTAL_ROOT` in `nwm-coastal/ecflow_demo`).
RUN_COASTAL_ROOT__HOST=${RUN_COASTAL_ROOT__HOST:-"${REPOS_COMMON_ROOT__HOST}/run_coastal"}

mkdir_p "${RUN_NGEN_ROOT__HOST}"
mkdir_p "${TGT_DIR_ESMF_DOMAIN}"
mkdir_p "${TGT_DIR_REGRID_WEIGHTS}"
mkdir_p "${RUN_COASTAL_ROOT__HOST}"

# ESMF mesh domain files. Each region subdirectory under
# s3://ngwpc-coastal/parm/ also holds other, unrelated files, so pull down
# just the GEOGRID_LDASOUT_Spatial_Metadata_* and geo_em_* files by name
# rather than syncing the whole subdirectory. Format per entry:
# "region_dir|source_filename|local_filename" -- source and local filename
# differ only for Puerto Rico's geo_em file (S3: geo_em_PRVI.nc, local
# convention: geo_em_Puerto_Rico.nc, matching esmf_mesh/NWM/domain/'s
# existing geo_em_Puerto_Rico.nc).
COASTAL_DOMAIN_FILES=(
    "domain|GEOGRID_LDASOUT_Spatial_Metadata_CONUS.nc|GEOGRID_LDASOUT_Spatial_Metadata_CONUS.nc"
    "domain|geo_em_CONUS.nc|geo_em_CONUS.nc"
    "domain_alaska|GEOGRID_LDASOUT_Spatial_Metadata_AK.nc|GEOGRID_LDASOUT_Spatial_Metadata_AK.nc"
    "domain_alaska|geo_em_AK.nc|geo_em_Alaska.nc"
    "domain_hawaii|GEOGRID_LDASOUT_Spatial_Metadata_HI.nc|GEOGRID_LDASOUT_Spatial_Metadata_HI.nc"
    "domain_hawaii|geo_em_HI.nc|geo_em_Hawaii.nc"
    "domain_puertorico|GEOGRID_LDASOUT_Spatial_Metadata_PRVI.nc|GEOGRID_LDASOUT_Spatial_Metadata_PRVI.nc"
    "domain_puertorico|geo_em_PRVI.nc|geo_em_Puerto_Rico.nc"
)

for entry in "${COASTAL_DOMAIN_FILES[@]}"; do
    IFS='|' read -r region_dir src_fname dst_fname <<< "${entry}"
    s3_copy_maybe_skip "${SOURCE_BUCKET_COASTAL}/${SOURCE_PREFIX_COASTAL_PARM}/${region_dir}/${src_fname}" \
        "${TGT_DIR_ESMF_DOMAIN}/${dst_fname}"
done

# Pre-computed ESMF regrid weights
s3_sync "${SOURCE_BUCKET_COASTAL}/${SOURCE_PREFIX_COASTAL_DEMO}/regrid_weights" "${TGT_DIR_REGRID_WEIGHTS}"

# Regionalization input data
s3_sync "${SOURCE_BUCKET_DEV}/${SOURCE_PREFIX_ROOT}/regionalization/data/inputs" "${MNT__NWM_REGION_MGR__INPUT_DATA}"

# run_coastal working directory (SCHISM/SFINCS model folders)
s3_sync "${SOURCE_BUCKET_COASTAL}/${SOURCE_PREFIX_COASTAL_DEMO}/run_coastal" "${RUN_COASTAL_ROOT__HOST}"

set -x
exit 0
