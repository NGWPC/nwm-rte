#!/bin/bash
set -euo pipefail

# Initial context. Note USER_NAME and USER_DIR can be different on some systems
WORK_DIR="$(realpath .)"  
USER_NAME="${USER%%@*}"

# Resolve USER_DIR (case-insensitive)
USER_DIR="$(find /home -maxdepth 1 -type d -iname "$USER_NAME" | head -n 1 || true)"
if [[ -z "$USER_DIR" ]]; then
    echo "ERROR: Could not locate home directory for user $USER_NAME under /home" >&2
    exit 1
fi

# Determine WORKSPACE_ROOT and REPOS_DIR based on environment
if [[ -d "/ngen-dev/$USER_NAME" ]]; then
    REPOS_DIR="/ngencerf-app/nwm-rte"
    export WORKSPACE_ROOT="/ngen-dev/$USER_NAME"
elif [[ -d "/ngen-oe/$USER_NAME" ]]; then
    REPOS_DIR="/ngencerf-app/nwm-rte"
    export WORKSPACE_ROOT="/ngen-oe/$USER_NAME"
else
    WORKSPACE_ROOT="$HOME"
    if [[ -d "$USER_DIR/repos" ]]; then
        REPOS_DIR="$USER_DIR/repos"
    elif [[ -d "$USER_DIR/ngwpc" ]]; then
        REPOS_DIR="$USER_DIR/ngwpc"
    else
        echo "ERROR: Could not find repos directory under $USER_DIR" >&2
        exit 1
    fi
fi

export WORKSPACE_ROOT
if [[ ! -w "$WORKSPACE_ROOT" ]]; then
    echo "ERROR: WORKSPACE_ROOT is not writable: $WORKSPACE_ROOT" >&2
    exit 1
fi

# Default workflow flags
parreg=false
formreg=false
ngen=false
eval=false
CONFIG_DIR="${WORK_DIR}/configs"

# Parse command line arguments
ARGS=$(getopt -o pfnehc:r: --long parreg,formreg,ngen,eval,help,config_dir:,repos: -- "$@")
if [ $? != 0 ]; then echo "Failed parsing options." >&2; exit 1; fi
eval set -- "$ARGS"

while true; do
    case "$1" in
        -p|--parreg) parreg=true; shift;;
        -f|--formreg) formreg=true; shift;;
        -n|--ngen) ngen=true; shift;;
        -e|--eval) eval=true; shift;;
        -c|--config_dir) CONFIG_DIR="$2"; shift 2;;
        -r|--repos) REPOS_DIR="$2"; shift 2;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]
Options:
  -p, --parreg         Run parameter regionalization (includes formulation)
  -f, --formreg        Run formulation regionalization only
  -n, --ngen           Run NGEN simulation
  -e, --eval           Run evaluation
  -c, --config_dir DIR Set config directory (default: ./configs)
  -r, --repos PATH     Set root directory for NGWPC repos 
  -h, --help           Show this message and exit
" >&2
            exit 0;;
        --) shift; break;;
        *) echo "Internal error!"; exit 1;;
    esac
done

# Validate workflow selection
selected=0
$parreg  && selected=$((selected + 1))
$formreg && selected=$((selected + 1))
$ngen    && selected=$((selected + 1))
$eval    && selected=$((selected + 1))

echo "Number of selected workflow steps: $selected"
if [[ $selected -eq 0 ]]; then
    echo "ERROR: No workflow specified to run. Use -h or --help for usage information." >&2
    exit 1
fi

# Determine RTE repo directory
RTE_REPO_DIR="$REPOS_DIR/nwm-rte"
if [[ ! -d "$RTE_REPO_DIR" ]]; then
    echo "ERROR: RTE repo not found at $RTE_REPO_DIR" >&2
    return 1 2>/dev/null || exit 1
fi

# Determine config directory
CONFIG_DIR="${WORK_DIR}/${CONFIG_DIR%/}"  # remove trailing slash if any
CONFIG_DIR="$(realpath "$CONFIG_DIR")"
if [[ ! -d "$CONFIG_DIR" ]]; then
    echo "ERROR: Config directory not found at $CONFIG_DIR" >&2
    return 1 2>/dev/null || exit 1
fi

# ensure work directory is restored on exit
trap 'cd "$WORK_DIR"' EXIT

# cd to RTE repo directory and source RTE settings
cd "$RTE_REPO_DIR"
source config.bashrc

# Ensure mount directories exist
ensure_dir() {
    [[ -d "$1" ]] || mkdir -p "$1"
    sudo chown -R "$(id -u):$(id -g)" "$1"
}
ensure_dir "$RUN_NGEN_ROOT__HOST/data/esmf_mesh"
ensure_dir "$RUN_NGEN_ROOT__HOST/data/scratch"
ensure_dir "$WORK_DIR/docker_logs/run"
ensure_dir "$WORK_DIR/bin_mounted"

# Docker run function
function docker_run {
    docker run \
        --entrypoint python \
        --user "$(id -u):$(id -g)" \
        -e HOME="$WORKSPACE_ROOT" \
        -e WORKSPACE_ROOT="$WORKSPACE_ROOT" \
        -v "$WORKSPACE_ROOT:$WORKSPACE_ROOT" \
        -w "$WORK_DIR" \
        -v "${CONFIG_DIR}:${CONFIG_DIR}" \
        -v "${RUN_NGEN_ROOT__HOST}/data/esmf_mesh/:/ngen-app/data/esmf_mesh/" \
        -v "${RUN_NGEN_ROOT__HOST}/data/scratch:/ngen-app/data/scratch" \
        -v "${WORK_DIR}/docker_logs/run:/ngencerf/data/run-logs" \
        -v "${WORK_DIR}/bin_mounted/:/ngen-app/bin/bin_mounted/" \
        -v "${REPOS_COMMON_ROOT__HOST}/nwm-region-mgr:/ngen-app/nwm-region-mgr" \
        -v "${REPOS_COMMON_ROOT__HOST}/nwm-verf/data:/ngen-app/nwm-verf/data" \
        --rm ${TARGET_IMAGE_NAME} "$@"
}

# Run requested workflow steps
SCRIPT="/ngen-app/bin/bin_mounted/run_regionalization.py"

$parreg  && docker_run "$SCRIPT" -c "$CONFIG_DIR" --parreg
$formreg && docker_run "$SCRIPT" -c "$CONFIG_DIR" --formreg
$ngen    && docker_run "$SCRIPT" -c "$CONFIG_DIR" --ngen
$eval    && docker_run "$SCRIPT" -c "$CONFIG_DIR" --eval
