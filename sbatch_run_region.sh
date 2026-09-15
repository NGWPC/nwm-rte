#!/bin/bash
set -euo pipefail

# -----------------------------------------------------------------------------
# sbatch_run_region.sh
#
## \brief
## Submits the regionalization workflow to SLURM using sbatch.
##
## \desc
## Usage:
##    ./sbatch_run_region.sh [CONFIG_DIR] [WORKFLOW_OPTIONS] [OPTIONS]
##
## \option CONFIG_DIR
## (optional, default: "configs") Directory containing configuration YAML files
##
## \option WORKFLOW_OPTIONS
## (optional, default: "parreg") Workflow steps to run: parreg, formreg, ngen, or eval
##
## \option --dry-run
## (optional switch) Print the generated SLURM script instead of submitting
##
## \option --image IMAGE
## (optional, default: "ghcr.io/ngwpc/nwm-rte") Docker image to use for the RTE
##
## \option --image-tag TAG
## (optional, default: "latest") Docker image tag to use for the RTE
##
## \option --script RUN_REGION_SCRIPT
## (optional, default: "/ngen-app/nwm-rte/run_region.sh")
## Path to the regionalization script to run inside the Docker container
##
## \option --walltime WALLTIME
## (optional, default: "48:00:00") Walltime for the SLURM job
##
## \option --pull-image
## (optional switch) Pull the latest Docker image before running
##
## \option --delete-runtime-dir
## (optional switch) Delete runtime directory after completion
##
## \option --help
## Display this help message and exit
##
# Examples:
##
## \example Do a dry-run to see the generated SLURM script
## \example-code bash
## ./sbatch_run_region.sh configs parreg ngen eval --dry-run
##
## \example Submit parameter regionalization
## \example-code bash
## ./sbatch_run_region.sh configs parreg
## ./sbatch_run_region.sh configs
##
## \example Submit formulation regionalization only
## \example-code bash
## ./sbatch_run_region.sh configs formreg
##
## \example Submit NGEN simulation with a different config directory
## \example-code bash
## ./sbatch_run_region.sh /ngen-oe/$USER/myconfigs ngen
##
## \example Submit evaluation only
## \example-code bash
## ./sbatch_run_region.sh configs eval
##
## \example Using a different Docker image
## \example-code bash
## ./sbatch_run_region.sh configs ngen --image ghcr.io/noaa-owp/nwm-rte
##
## \example Using an image tag other than 'latest'
## \example-code bash
## ./sbatch_run_region.sh configs ngen --image-tag "069ad0f6d332"
##
## \example Pull the latest image before running
## \example-code bash
## ./sbatch_run_region.sh configs ngen --pull-image
##
## \example Delete runtime directory after completion
## \example-code bash
## ./sbatch_run_region.sh configs ngen --delete-runtime-dir
##
## \example Use a different regionalization script
## \example-code bash
## ./sbatch_run_region.sh configs parreg --script ./rte-scripts/run_region.sh
##
## \example Specify walltime for the SLURM job
## \example-code bash
## ./sbatch_run_region.sh configs ngen --walltime "04:00:00"
##
## \example Display help
## \example-code bash
## ./sbatch_run_region.sh --help
##
# -----------------------------------------------------------------------------

OPTIONS=()
DRY_RUN=false
IMAGE="ghcr.io/ngwpc/nwm-rte"
IMAGE_TAG="latest"
RUN_REGION_SCRIPT="/ngen-app/nwm-rte/run_region.sh"
PULL_IMAGE=false
DELETE_RUNTIME_DIR=false
WALLTIME="48:00:00"

show_help() {
    cat <<EOF
Usage:
  $0 [CONFIG_DIR] [WORKFLOW_OPTIONS] [OPTIONS]

Submit the regionalization workflow to SLURM using sbatch.

CONFIG_DIR:
  Optional directory containing configuration YAML files.
  Default: configs

WORKFLOW_OPTIONS:
  Optional workflow steps to run. Valid options:
    parreg
    formreg
    ngen
    eval

  Default: parreg

OPTIONS:
  --dry-run
      Print the generated SLURM script instead of submitting it.

  --image IMAGE
      Docker image to use for the RTE.
      Default: $IMAGE

  --image-tag TAG
      Docker image tag to use for the RTE.
      Default: $IMAGE_TAG

  --script SCRIPT
      Regionalization script to run inside the Docker container.
      Default: $RUN_REGION_SCRIPT

  --walltime WALLTIME
      Walltime for the SLURM job.
      Default: $WALLTIME

  --pull-image
      Pull the latest Docker image before running.

  --delete-runtime-dir
      Delete the runtime directory after completion.

  --help
      Display this help message and exit.

Examples:
  Submit parameter regionalization:
    $0 configs parreg

  Submit the default workflow:
    $0 configs

  Submit formulation regionalization:
    $0 configs formreg

  Submit NGEN simulation:
    $0 configs ngen

  Submit evaluation:
    $0 configs eval

  Use a different Docker image:
    $0 configs ngen --image ghcr.io/noaa-owp/nwm-rte

  Use a different image tag:
    $0 configs ngen --image-tag 069ad0f6d332

  Pull the latest image before running:
    $0 configs ngen --pull-image

  Delete the runtime directory after completion:
    $0 configs ngen --delete-runtime-dir

  Use a different regionalization script:
    $0 configs parreg --script ./rte-scripts/run_region.sh

  Specify walltime for the SLURM job:
    $0 configs ngen --walltime "04:00:00"

  Print the generated SLURM script without submitting:
    $0 configs parreg ngen eval --dry-run

EOF
    exit 0
}

# Handle --help before processing CONFIG_DIR.
if [[ $# -gt 0 && "$1" == "--help" ]]; then
    show_help
fi

# CONFIG_DIR is the first argument only if it is not an option.
if [[ $# -gt 0 && "$1" != -* ]]; then
    CONFIG_DIR="$(realpath "$1")"
    shift
else
    CONFIG_DIR="$(realpath "configs")"
fi

if [[ ! -d "${CONFIG_DIR}" ]]; then
    echo "ERROR: Config directory '${CONFIG_DIR}' does not exist." >&2
    exit 1
fi
export CONFIG_DIR


while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --image)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --image requires a value." >&2
                exit 1
            fi
            IMAGE="$2"
            shift 2
            ;;
        --image-tag)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --image-tag requires a value." >&2
                exit 1
            fi
            IMAGE_TAG="$2"
            shift 2
            ;;
        --script)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --script requires a value." >&2
                exit 1
            fi
            RUN_REGION_SCRIPT="$2"
            shift 2
            ;;
        --walltime)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --walltime requires a value." >&2
                exit 1
            fi
            WALLTIME="$2"
            shift 2
            ;;
        --pull-image)
            PULL_IMAGE=true
            shift
            ;;
        --delete-runtime-dir)
            DELETE_RUNTIME_DIR=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            OPTIONS+=("$1")
            shift
            ;;
    esac
done

# Make sure $RUN_REGION_SCRIPT exists.
if [[ ! -f "$RUN_REGION_SCRIPT" ]]; then
    echo "ERROR: Run region script '$RUN_REGION_SCRIPT' does not exist." >&2
    exit 1
fi

# Default workflow option.
if [[ ${#OPTIONS[@]} -eq 0 ]]; then
    OPTIONS=("parreg")
fi

# Validate workflow options.
VALID_OPTIONS=(formreg parreg ngen eval)
for opt in "${OPTIONS[@]}"; do
    if [[ ! " ${VALID_OPTIONS[*]} " =~ " ${opt} " ]]; then
        echo "ERROR: Invalid workflow option '${opt}'. Valid options: ${VALID_OPTIONS[*]}" >&2
        exit 1
    fi
done

# Sort options in canonical order.
SORTED_OPTIONS=()
for valid in "${VALID_OPTIONS[@]}"; do
    for opt in "${OPTIONS[@]}"; do
        [[ "$opt" == "$valid" ]] && SORTED_OPTIONS+=("$opt")
    done
done
OPTIONS=("${SORTED_OPTIONS[@]}")

# Build combined workflow flags.
OPTION_FLAGS=()
for opt in "${OPTIONS[@]}"; do
    OPTION_FLAGS+=("--$opt")
done

if $PULL_IMAGE; then
    OPTION_FLAGS+=("--pull-image")
fi

if $DELETE_RUNTIME_DIR; then
    OPTION_FLAGS+=("--delete-runtime-dir")
fi

# Determine total number of tasks (n_procs).
NTASKS=$(python3 - <<'EOF'
import os
from pathlib import Path

import yaml

cfg = yaml.safe_load(
    (Path(os.environ["CONFIG_DIR"]) / "config_general.yaml").read_text()
)
n_procs = int(cfg["general"].get("n_procs", 0))
print(max(n_procs, 1))
EOF
)

# Get all idle nodes and their CPU counts.
IDLE_NODES=$(sinfo -h -t idle -N -o "%N %c %P")

# Select the idle node with the fewest CPUs that can satisfy NTASKS.
NODE_INFO=$(echo "$IDLE_NODES" |
    awk -v n="$NTASKS" '$2 >= n {print}' |
    sort -k2n |
    head -n1)

NODE_NAME=$(echo "$NODE_INFO" | awk '{print $1}')
NODE_PART=$(echo "$NODE_INFO" | awk '{print $3}' | sed 's/\*$//')

if [[ -z "$NODE_NAME" ]]; then
    echo "ERROR: No idle node has enough CPUs for NTASKS=$NTASKS" >&2
    exit 1
fi

echo "Submitting job with the following parameters:"
echo "  options       = ${OPTIONS[*]}"
echo "  ntasks        = $NTASKS"
echo "  nodes         = 1"
echo "  node          = $NODE_NAME"
echo "  partition     = $NODE_PART"
echo "  cpus-per-task = 1"
echo "  config_dir    = $CONFIG_DIR"
echo "  image         = $IMAGE"
echo "  image_tag     = $IMAGE_TAG"
echo "  script        = $RUN_REGION_SCRIPT"
echo "  walltime      = $WALLTIME"
echo

JOB_SUFFIX=$(IFS=-; echo "${OPTIONS[*]}")

SBATCH_SCRIPT=$(cat <<EOF
#!/bin/bash
#SBATCH --job-name=region-${JOB_SUFFIX}
#SBATCH --nodes=1
#SBATCH --ntasks=$NTASKS
#SBATCH --cpus-per-task=1
#SBATCH --nodelist=$NODE_NAME
#SBATCH --partition=$NODE_PART
#SBATCH --time=$WALLTIME
#SBATCH --output=logs/region-${JOB_SUFFIX}-%j.log
#SBATCH --error=logs/region-${JOB_SUFFIX}-%j.log

set -euo pipefail

echo "Job started on nodes: \$SLURM_JOB_NODELIST"
echo "Nodes allocated: \$SLURM_JOB_NUM_NODES"
echo "Running on directory: \$SLURM_SUBMIT_DIR"
echo "Job ID: \$SLURM_JOB_ID"

"${RUN_REGION_SCRIPT}" "${OPTION_FLAGS[@]}" -c "${CONFIG_DIR}" --image "${IMAGE}" --image-tag "${IMAGE_TAG}"
EOF
)

echo "===== sbatch script ====="
echo "$SBATCH_SCRIPT"
echo "========================="

if $DRY_RUN; then
    echo "DRY RUN"
    exit 0
fi

echo "$SBATCH_SCRIPT" | sbatch
echo "Job submitted."