#!/bin/bash
set -euo pipefail

# -----------------------------------------------------------------------------
# run_region.sh
#
## \brief
## Script to run NWM regionalization, NGEN simulation, and evaluation workflows using an RTE Docker container.
## 
## \desc
## Takes no positional arguments. Workflow steps are specified using named command-line arguments.
## 
## \usage
## <root-path-to-script>/run_region.sh [OPTIONS]
## 
# Arguments:
## \option -p, --parreg
## Run parameter regionalization (includes formulation)
## \option -f, --formreg
## Run formulation regionalization only
## \option -n, --ngen
## Run NGEN simulation
## \option -e, --eval
## Run evaluation
## \option -c, --config-dir DIR
## (default: `"./configs"`) Set config directory
## \option -r, --rte-path PATH
## (default: `"$(realpath .)/rte_scripts"`) Set path to the directory containing RTE scripts
## \option -i, --image
## (default: ghcr.io/ngwpc/nwm-rte) Set Docker image to use for running the workflows
## \option -t, --image-tag TAG
## (default: `"latest"`) Set Docker image tag
## \option --pull-image
## (optional switch) Pull the latest Docker image before running
## \option -d, --delete-runtime-dir
## (optional switch) Delete runtime directory after completion
## \option -h, --help
## Show this message and exit
## 
# Examples:
## \example Run parameter regionalization
## \example-code bash
## #Sample config files can be found in nwm-region-mgr repo under configs directory
## ./nwm-rte/run_region.sh --parreg
## ./nwm-rte/run_region.sh --parreg -c configs
## ./nwm-rte/run_region.sh -p -c configs
## ./nwm-rte/run_region.sh -p -c ~/ngwpc/nwm-region-mgr/configs
##
## \example Run formulation regionalization only
## \example-code bash
## ./nwm-rte/run_region.sh --formreg -c configs
##
## \example Run NGEN simulation
## \example-code bash
## ./nwm-rte/run_region.sh --ngen -c configs
##
## \example Run evaluation
## \example-code bash
## ./nwm-rte/run_region.sh --eval -c configs
##
## \example Run multiple steps
## \example-code bash
## ./nwm-rte/run_region.sh --parreg --ngen -c configs
##
## \example Run with run_regionalization.py at a different location (default: ./rte_scripts/run_regionalization.py)
## \example-code bash
## ./nwm-rte/run_region.sh --ngen -c configs -r ~/repos/nwm-rte/bin_mounted/ngen_rte
## (where -r specifies the path to the directory containing RTE scripts)
##
## \example Run with different Docker image & tag
## \example-code bash
## ./nwm-rte/run_region.sh --ngen -c configs -i ghcr.io/noaa-owp/nwm-rte -t pr-20-build
##
## \example Run with pulling the latest Docker image before running
## \example-code bash
## ./nwm-rte/run_region.sh --ngen -c configs --pull-image
##
## \example Delete runtime directory after completion (default: keep for debugging)
## \example-code bash
## ./nwm-rte/run_region.sh -c configs -p -n -e -d
## 
# -----------------------------------------------------------------------------

# Default workflow flags
parreg=false
formreg=false
ngen=false
do_eval=false
CONFIG_DIR="$(realpath .)/configs"
IMAGE="ghcr.io/ngwpc/nwm-rte"
IMAGE_TAG="latest"
PULL_IMAGE=false
DELETE_RUNTIME_DIR=false
RTE_PATH="$(dirname "$(realpath "$0")")/bin_mounted/ngen_rte"

# Parse command line arguments
if ! ARGS=$(getopt -o pfnehc:r:i:t:d \
    --long parreg,formreg,ngen,eval,help,config-dir:,rte-path:,image:,image-tag:,pull-image,delete-runtime-dir \
    -n "$0" -- "$@"); then
    echo "Failed parsing options." >&2
    exit 1
fi

eval set -- "$ARGS"

while true; do
    case "$1" in
        -p|--parreg) parreg=true; shift;;
        -f|--formreg) formreg=true; shift;;
        -n|--ngen) ngen=true; shift;;
        -e|--eval) do_eval=true; shift;;
        -c|--config-dir) CONFIG_DIR="$2"; shift 2;;
        -r|--rte-path) RTE_PATH="$2"; shift 2;;
        -i|--image) IMAGE="$2"; shift 2;;
        -t|--image-tag) IMAGE_TAG="$2"; shift 2;;
        --pull-image) PULL_IMAGE=true; shift;;
        -d|--delete-runtime-dir) DELETE_RUNTIME_DIR=true; shift;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]
Options:
  -p, --parreg                 Run parameter regionalization (includes formulation)
  -f, --formreg                Run formulation regionalization only
  -n, --ngen                   Run NGEN simulation
  -e, --eval                   Run evaluation
  -c, --config-dir             Set config directory (default: ./configs)
  -r, --rte-path               Set path to the RTE scripts folder (default: "./rte_scripts")
  -i, --image                  Set Docker image (default: ghcr.io/ngwpc/nwm-rte)
  -t, --image-tag              Set Docker image tag (default: latest)
  --pull-image                 Pull the latest Docker image (default: false) before running
  -d, --delete-runtime-dir     Delete runtime directory after completion (default: keep for debugging)
  -h, --help                   Show this message and exit
" >&2
            exit 0;;
        --) shift; break;;
        *) echo "Internal error!"; exit 1;;
    esac
done

# make sure $HOME is set
if [ -z "${HOME:-}" ]; then
    echo "ERROR: HOME environment variable is not set." >&2
    exit 1
fi

# Validate workflow selection
selected_workflows=()
$parreg  && selected_workflows+=("parreg")
$formreg && selected_workflows+=("formreg")
$ngen    && selected_workflows+=("ngen")
$do_eval && selected_workflows+=("eval")

if [[ ${#selected_workflows[@]} -eq 0 ]]; then
    echo "ERROR: No workflow specified to run. Use -h or --help for usage information." >&2
    exit 1
fi
echo "Selected workflows: ${selected_workflows[*]}"

# function to create runtime directory if it doesn't exist and set ownership to current user (for docker permissions)
ensure_dir() {
    mkdir -p "$1"
    chown -R "$(id -u):$(id -g)" "$1" 2>/dev/null || true
}

# function to make sure directory already exists on host; error out if otherwise
require_dir() {
    local dir="$1"

    if [ ! -d "$dir" ]; then
        echo "ERROR: Required directory does not exist: $dir" >&2
        exit 1
    fi
}

# Function to make sure required config files exist
require_config_files() {
    local mode="$1"
    local required_files=(
        "$CONFIG_DIR/config_general.yaml"
    )
    local missing_files=()

    if [ "$mode" = "parreg" ]; then
        required_files+=(
            "$CONFIG_DIR/config_formreg.yaml"
            "$CONFIG_DIR/config_parreg.yaml"
        )
    elif [ "$mode" = "formreg" ]; then
        required_files+=(
            "$CONFIG_DIR/config_formreg.yaml"
        )
    elif [ "$mode" = "ngen" ]; then
        required_files+=(
            "$CONFIG_DIR/config_ngen.yaml"
        )
    elif [ "$mode" = "eval" ]; then
        required_files+=(
            "$CONFIG_DIR/config_eval.yaml"
        )
    else
        echo "ERROR: Unknown mode: $mode" >&2
        exit 1
    fi

    # Check all required files
    for config_file in "${required_files[@]}"; do
        if [ ! -f "$config_file" ]; then
            missing_files+=("$config_file")
        fi
    done

    # Report all missing files
    if [ ${#missing_files[@]} -gt 0 ]; then
        echo "ERROR: The following required config files are missing:" >&2
        for config_file in "${missing_files[@]}"; do
            echo "  - $config_file" >&2
        done
        exit 1
    fi
}

# expand and resolve CONFIG_DIR
CONFIG_DIR="${CONFIG_DIR/#\~/$HOME}"
CONFIG_DIR="$(realpath "$CONFIG_DIR")"
require_dir "$CONFIG_DIR"

# make sure required config files exist for the selected workflows
$formreg && require_config_files "formreg"
$parreg  && require_config_files "parreg"
$ngen    && require_config_files "ngen"
$do_eval && require_config_files "eval"

# Extract directories from config_general.yaml
CONFIG_FILE="${CONFIG_DIR}/config_general.yaml"
WORK_DIR=$(sed -n "s/^[[:space:]]*base_dir:[[:space:]]*//p" "$CONFIG_FILE" |
    sed 's/[[:space:]]*#.*$//' |
    sed "s/^[[:space:]]*['\"]//; s/['\"][[:space:]]*$//")

STATIC_DATA_DIR=$(sed -n "s/^[[:space:]]*static_data_dir:[[:space:]]*//p" "$CONFIG_FILE" |
    sed 's/[[:space:]]*#.*$//' |
    sed "s/^[[:space:]]*['\"]//; s/['\"][[:space:]]*$//")

# Expand a leading "~" if any
WORK_DIR="${WORK_DIR/#\~/$HOME}"
STATIC_DATA_DIR="${STATIC_DATA_DIR/#\~/$HOME}"
RTE_PATH="${RTE_PATH/#\~/$HOME}"

ensure_dir "$WORK_DIR"
require_dir "$STATIC_DATA_DIR"
require_dir "$RTE_PATH"

echo "WORK_DIR: $WORK_DIR"
echo "STATIC_DATA_DIR: $STATIC_DATA_DIR"
echo "RTE_PATH: $RTE_PATH"

# ensure required static forcing data exists on host
FORCING_STATIC_DIR="${STATIC_DATA_DIR}/ngen"
require_dir "$FORCING_STATIC_DIR"

# create run-time temporary directory with timestamp to avoid conflicts between simultaneous runs
RUNTIME_DIR_TMP=$(mktemp -d "${WORK_DIR}/run_time_XXXXXXXX")
ensure_dir "$RUNTIME_DIR_TMP"
chmod a+rx "${RUNTIME_DIR_TMP}"
echo "Created run-time temporary directory: ${RUNTIME_DIR_TMP}."

# create runtime directories for forcing
ensure_dir "$RUNTIME_DIR_TMP/run_ngen/data/scratch"
ensure_dir "$RUNTIME_DIR_TMP/run_ngen/data/esmf_mesh"

# create docker logs directory
ensure_dir "$RUNTIME_DIR_TMP/docker_logs/run"

cleanup() {
  rc=$?
  if [[ -n "${RUNTIME_DIR_TMP:-}" && -d "${RUNTIME_DIR_TMP}" ]]; then
    echo "Cleanup (exit=$rc): removing ${RUNTIME_DIR_TMP}"
    rm -rf "${RUNTIME_DIR_TMP}" || true
  fi
}

if $DELETE_RUNTIME_DIR; then
    echo "Runtime directory will be deleted after completion as requested."
    trap cleanup EXIT
fi

# Python module to run with docker run
RUN_REGION_MODULE="run_regionalization"

# Parent dir of where run_regionalization.py is mounted inside the container (for setting PYTHONPATH)
CONTAINER_PYTHONPATH_ENTRY="${RTE_PATH}"

# docker image to use
TARGET_IMAGE_NAME="${IMAGE}:${IMAGE_TAG}"
echo "Using Docker image: ${TARGET_IMAGE_NAME}"

# pull the latest image if requested
if $PULL_IMAGE || ! docker image inspect "${TARGET_IMAGE_NAME}" >/dev/null 2>&1; then
    echo "Pulling Docker image: ${TARGET_IMAGE_NAME}"
    docker pull "${TARGET_IMAGE_NAME}"
fi

CONTAINER_PYTHONPATH_EXISTING="$(docker run --rm --entrypoint sh ${TARGET_IMAGE_NAME} -lc 'printf "%s" "$PYTHONPATH"')"
CONTAINER_PYTHONPATH_COMBINED="${CONTAINER_PYTHONPATH_EXISTING}:${CONTAINER_PYTHONPATH_ENTRY}"
echo "Combined PYTHONPATH for the container: ${CONTAINER_PYTHONPATH_COMBINED}"

# docker run function to execute the regionalization workflow inside the container
# note $HOME/.local is mounted inside the container for cartopy (used by nwm-eval-mgr)
ensure_dir "$HOME/.local"
function docker_run {
    docker run \
        --entrypoint python \
        --user "$(id -u):$(id -g)" \
        -e HOME="$HOME" \
        -e PYTHONPATH="${CONTAINER_PYTHONPATH_COMBINED}" \
        -e WORK_DIR="$WORK_DIR" \
        -e STATIC_DATA_DIR="$STATIC_DATA_DIR" \
        -w "${WORK_DIR}" \
        -v "${HOME}/.local/:${HOME}/.local/:rw" \
        -v "${WORK_DIR}:${WORK_DIR}:rw" \
        -v "${STATIC_DATA_DIR}:${STATIC_DATA_DIR}:ro" \
        -v "${RTE_PATH}:${RTE_PATH}:ro" \
        -v "${CONFIG_DIR}:${CONFIG_DIR}:ro" \
        -v "${FORCING_STATIC_DIR}:/ngencerf-app/static_data:ro" \
        -v "${RUNTIME_DIR_TMP}/run_ngen/data:/ngencerf-app/runtime_data:rw" \
        -v "${RUNTIME_DIR_TMP}/docker_logs/run:/ngencerf/data/run-logs:rw" \
        --rm "${TARGET_IMAGE_NAME}" -um "$@"
}

# Run requested workflow steps using Docker
$parreg  && docker_run "$RUN_REGION_MODULE" -c "$CONFIG_DIR" --parreg
$formreg && docker_run "$RUN_REGION_MODULE" -c "$CONFIG_DIR" --formreg
$ngen    && docker_run "$RUN_REGION_MODULE" -c "$CONFIG_DIR" --ngen
$do_eval && docker_run "$RUN_REGION_MODULE" -c "$CONFIG_DIR" --eval

echo "All requested workflows (${selected_workflows[*]}) completed successfully."
exit 0