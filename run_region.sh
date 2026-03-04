#!/bin/bash
set -euo pipefail

# -----------------------------------------------------------------------------
# run_region.sh
#
# Script to run NWM regionalization, NGEN simulation, and evaluation workflows
# based on command line options.
#
# Usage:
#   cd [working_directory, e.g., /ngen-oe/$USER/run_region, /ngen-dev/$USER/run_region, or ~/run_region]
#   [NWM-RTE_ROOT]/run_region.sh [OPTIONS]
#
# Arguments:
#   -p, --parreg         Run parameter regionalization (includes formulation)
#   -f, --formreg        Run formulation regionalization only
#   -n, --ngen           Run NGEN simulation
#   -e, --eval           Run evaluation
#   -c, --config_dir DIR Set config directory (default: ./configs)
#   -r, --repos PATH     Set root directory for NGWPC repos (default: auto-detect)
#   -t, --image-tag TAG  Set Docker image tag (default: latest)
#   -i, --pull-image     Pull the latest Docker image before running (optional)
#   -h, --help           Show this message and exit
#
# Examples:
#   # Run parameter regionalization
#   # Sample config files can be found in nwm-region-mgr repo under configs directory
#   /ngencerf-app/nwm-rte/run_region.sh --parreg -c configs
#   ~/ngwpc/nwm-rte/run_region.sh --parreg -c configs
#   ~/ngwpc/nwm-rte/run_region.sh -p -c configs
#   ~/ngwpc/nwm-rte/run_region.sh -p -c ~/ngwpc/nwm-region-mgr/configs
#
#   # Run formulation regionalization only
#   /ngencerf-app/nwm-rte/run_region.sh --formreg -c configs
#
#  # Run NGEN simulation
#   /ngencerf-app/nwm-rte/run_region.sh --ngen -c configs
#
#  # Run evaluation
#   /ngencerf-app/nwm-rte/run_region.sh --eval -c configs
#
#  # Run multiple steps
#   /ngencerf-app/nwm-rte/run_region.sh --parreg --ngen -c configs
#
#  # Run with different repos root directory
#   /ngencerf-app/nwm-rte/run_region.sh --ngen -c configs -r /ngen-oe/$USER
#
#  # Run with different Docker image tag
#   /ngencerf-app/nwm-rte/run_region.sh --ngen -c configs -t pr-20-build
#
#  # Run with pulling the latest Docker image before running
#  /ngencerf-app/nwm-rte/run_region.sh --ngen -c configs -i
# -----------------------------------------------------------------------------

# Initial context
WORK_DIR="$(realpath .)"  
USER_NAME="${USER%%@*}"

# Determine REPOS_COMMON_ROOT__HOST (NGWPC repos) based on environment
if [[ -d "/ngen-dev/$USER_NAME" ]]; then
    REPOS_COMMON_ROOT__HOST="/ngencerf-app"
elif [[ -d "/ngen-oe/$USER_NAME" ]]; then
    REPOS_COMMON_ROOT__HOST="/ngencerf-app"
else
    # Resolve USER_DIR (case-insensitive)
    # Note USER_NAME and USER_DIR can be different on some systems
    USER_DIR="$(find /home -maxdepth 1 -type d -iname "$USER_NAME" | head -n 1 || true)"
    if [[ -z "$USER_DIR" ]]; then
        echo "ERROR: Could not locate home directory for user $USER_NAME under /home" >&2
        exit 1
    fi

    if [[ -d "$USER_DIR/repos" ]]; then
        REPOS_COMMON_ROOT__HOST="$USER_DIR/repos"
    elif [[ -d "$USER_DIR/ngwpc" ]]; then
        REPOS_COMMON_ROOT__HOST="$USER_DIR/ngwpc"
    fi
fi

export WORK_DIR
if [[ ! -w "$WORK_DIR" ]]; then
    echo "ERROR: WORK_DIR is not writable: $WORK_DIR" >&2
    exit 1
fi

# Default workflow flags
parreg=false
formreg=false
ngen=false
eval=false
CONFIG_DIR="${WORK_DIR}/configs"
IMAGE_TAG="latest"
PULL_IMAGE=false

# Parse command line arguments
ARGS=$(getopt -o pfnehc:r:t:i --long parreg,formreg,ngen,eval,help,config_dir:,repos:,image-tag:,pull-image -- "$@")
if [ $? != 0 ]; then echo "Failed parsing options." >&2; exit 1; fi
eval set -- "$ARGS"

while true; do
    case "$1" in
        -p|--parreg) parreg=true; shift;;
        -f|--formreg) formreg=true; shift;;
        -n|--ngen) ngen=true; shift;;
        -e|--eval) eval=true; shift;;
        -c|--config_dir) CONFIG_DIR="$2"; shift 2;;
        -r|--repos) REPOS_COMMON_ROOT__HOST="$2"; shift 2;;
        -t|--image-tag) IMAGE_TAG="$2"; shift 2;;
        -i|--pull-image) PULL_IMAGE=true; shift;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]
Options:
  -p, --parreg         Run parameter regionalization (includes formulation)
  -f, --formreg        Run formulation regionalization only
  -n, --ngen           Run NGEN simulation
  -e, --eval           Run evaluation
  -c, --config_dir DIR Set config directory (default: ./configs)
  -r, --repos PATH     Set root directory for NGWPC repos 
  -t, --image-tag TAG  Set Docker image tag (default: latest)
  -i, --pull-image     Pull the latest Docker image (with tag "latest" or as specified by --image-tag) before running (optional)
  -h, --help           Show this message and exit
" >&2
            exit 0;;
        --) shift; break;;
        *) echo "Internal error!"; exit 1;;
    esac
done

# Validate workflow selection
selected_workflows=()
$parreg  && selected_workflows+=("parreg")
$formreg && selected_workflows+=("formreg")
$ngen    && selected_workflows+=("ngen")
$eval    && selected_workflows+=("eval")

if [[ ${#selected_workflows[@]} -eq 0 ]]; then
    echo "ERROR: No workflow specified to run. Use -h or --help for usage information." >&2
    exit 1
fi
echo "Selected workflows: ${selected_workflows[*]}"

# make sure REPOS_COMMON_ROOT__HOST is set
if [[ -z "${REPOS_COMMON_ROOT__HOST:-}" ]]; then
    echo "ERROR: REPOS_COMMON_ROOT__HOST is not set and could not be auto-detected (/ngencerf-app on INT/EA/UAT; ~/repos or ~/ngwpc in AWS workspace)."
    echo "Please specify with -r or --repos option." >&2
    exit 1
fi

# Determine config directory
CONFIG_DIR="$(realpath "$CONFIG_DIR")"
if [[ ! -d "$CONFIG_DIR" ]]; then
    echo "ERROR: Config directory not found at $CONFIG_DIR" >&2
    exit 1
fi

# function to create runtime directory if it doesn't exist and set ownership to current user (for docker permissions)
ensure_dir() {
    mkdir -p "$1"
    chown -R "$(id -u):$(id -g)" "$1" 2>/dev/null || true
}

# function to make sure directory already exists on host; error out if otherwise
require_dir() {
    local dir="$1"

    if [ ! -d "$dir" ]; then
        echo "Error: Required directory does not exist: $dir" >&2
        exit 1
    fi
}

# ensure static data directory exists on host (currently required for ngen-forcing)
require_dir "${REPOS_COMMON_ROOT__HOST}/run_ngen/data"

# ensure ngen-forcing config template folder exists on host
forcing_config_dir="${REPOS_COMMON_ROOT__HOST}/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates"
require_dir "${forcing_config_dir}"

# Create run-time temporary directory with timestamp to avoid conflicts between simultaneous runs
RUNTIME_DIR_TMP=$(mktemp -d "${WORK_DIR}/run_time_XXXXXXXX")
ensure_dir "$RUNTIME_DIR_TMP"

# create runtime directories for forcing
ensure_dir "$RUNTIME_DIR_TMP/run_ngen/data/scratch"
ensure_dir "$RUNTIME_DIR_TMP/run_ngen/data/esmf_mesh"

# create docker logs directory
ensure_dir "$RUNTIME_DIR_TMP/docker_logs/run"

# home dir inside container (required for some packages in nwm-verf and nwm-region-mgr)
ensure_dir "$RUNTIME_DIR_TMP/home"

echo "Created run-time temporary directory: ${RUNTIME_DIR_TMP}. Will be removed after run is complete."

cleanup() {
  rc=$?
  if [[ -n "${RUNTIME_DIR_TMP:-}" && -d "${RUNTIME_DIR_TMP}" ]]; then
    echo "Cleanup (exit=$rc): removing ${RUNTIME_DIR_TMP}"
    rm -rf "${RUNTIME_DIR_TMP}" || true
  fi
}

trap cleanup EXIT

# script to run with docker run
SCRIPT="${REPOS_COMMON_ROOT__HOST}/nwm-rte/bin_mounted/run_regionalization.py"

# docker image to use
TARGET_IMAGE_NAME="ghcr.io/ngwpc/nwm-rte:${IMAGE_TAG}"
#TARGET_IMAGE_NAME=ngen_rte:ghcr # Using local image for testing

echo "Using Docker image: ${TARGET_IMAGE_NAME}"

# pull the latest image if requested
if $PULL_IMAGE || ! docker image inspect "${TARGET_IMAGE_NAME}" >/dev/null 2>&1; then
    echo "Pulling Docker image: ${TARGET_IMAGE_NAME}"
    docker pull "${TARGET_IMAGE_NAME}"
fi

# Docker run function
# To run ngen-forcing with debug log, add below: -e "FORCING_LOGLEVEL=DEBUG" \
function docker_run {
    docker run \
        --entrypoint python \
        --user "$(id -u):$(id -g)" \
        -e WORK_DIR="${WORK_DIR}" \
        -e REPOS_COMMON_ROOT__HOST="${REPOS_COMMON_ROOT__HOST}" \
        -e HOME="${RUNTIME_DIR_TMP}/home" \
        -w "${WORK_DIR}" \
        -v "${WORK_DIR}:${WORK_DIR}" \
        -v "${REPOS_COMMON_ROOT__HOST}:${REPOS_COMMON_ROOT__HOST}" \
        -v "${REPOS_COMMON_ROOT__HOST}/run_ngen/data:/ngencerf-app/static_data" \
        -v "${forcing_config_dir}:/ngencerf-app/forcing_config_templates" \
        -v "${CONFIG_DIR}:${CONFIG_DIR}" \
        -v "${RUNTIME_DIR_TMP}/run_ngen/data:/ngencerf-app/runtime_data" \
        -v "${RUNTIME_DIR_TMP}/docker_logs/run:/ngencerf/data/run-logs" \
        --rm ${TARGET_IMAGE_NAME} "$@"
}

# Run requested workflow steps
$parreg  && docker_run "$SCRIPT" -c "$CONFIG_DIR" --parreg
$formreg && docker_run "$SCRIPT" -c "$CONFIG_DIR" --formreg
$ngen    && docker_run "$SCRIPT" -c "$CONFIG_DIR" --ngen
$eval    && docker_run "$SCRIPT" -c "$CONFIG_DIR" --eval

echo "All requested workflows (${selected_workflows[*]}) completed successfully."
exit 0