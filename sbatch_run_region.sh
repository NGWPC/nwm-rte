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
## \option -n, --dry-run
## (optional switch) Print the generated SLURM script instead of submitting
##
## \option -i, --image IMAGE
## (optional, default: "ghcr.io/ngwpc/nwm-rte") Docker image to use for the RTE
##
## \option -t, --image-tag TAG
## (optional, default: "latest") Docker image tag to use for the RTE
##
## \option -s, --script RUN_REGION_SCRIPT
## (optional, default: "/ngen-app/nwm-rte/run_region.sh")
## Path to the regionalization script to run inside the Docker container
##
## \option -w, --walltime WALLTIME
## (optional, default: "48:00:00") Walltime for the SLURM job
##
## \option -p, --pull-image
## (optional switch) Pull the latest Docker image before running
##
## \option -d, --delete-runtime-dir
## (optional switch) Delete runtime directory after completion
##
## \option -h, --help
## Display this help message and exit
##
# -----------------------------------------------------------------------------

OPTIONS=()
DRY_RUN=false
IMAGE="ghcr.io/ngwpc/nwm-rte"
IMAGE_TAG="latest"
PULL_IMAGE=false
DELETE_RUNTIME_DIR=false
WALLTIME="48:00:00"
RUN_REGION_SCRIPT="$(dirname "$(realpath "$0")")/run_region.sh"

show_help() {
    cat <<EOF
Usage:
  $0 [CONFIG_DIR] [WORKFLOW_OPTIONS] [OPTIONS]

Submit the regionalization workflow to SLURM using sbatch.

CONFIG_DIR:
  Optional directory containing configuration YAML files. If specified, it must
  precede any workflow options.
  Default: configs

WORKFLOW_OPTIONS:
  Optional workflow steps to run. Valid options:
    parreg
    formreg
    ngen
    eval

  Default: parreg

OPTIONS:
  -n, --dry-run
      Print the generated SLURM script instead of submitting it.

  -i, --image IMAGE
      Docker image to use for running regionalization.
      Default: $IMAGE

  -t, --image-tag TAG
      Docker image tag to use for running regionalization.
      Default: $IMAGE_TAG

  -s, --script SCRIPT
      Regionalization script to run inside the Docker container.
      Default: $RUN_REGION_SCRIPT

  -w, --walltime WALLTIME
      Walltime for the SLURM job.
      Default: $WALLTIME

  -p, --pull-image
      Pull the latest Docker image before running.

  -d, --delete-runtime-dir
      Delete the runtime directory after completion.

  -h, --help
      Display this help message and exit

Examples:
  Submit default workflow with default configuration directory configs/:
    $0

  Submit formulation regionalization:
    $0 configs formreg

  Submit NGEN simulation:
    $0 configs ngen

  Submit evaluation:
    $0 configs eval

  Use a different Docker image:
    $0 configs ngen --image ghcr.io/noaa-owp/nwm-rte
    $0 configs ngen -i ghcr.io/noaa-owp/nwm-rte

  Use a different image tag:
    $0 configs ngen --image-tag 069ad0f6d332
    $0 configs ngen -t 069ad0f6d332

  Pull the latest image before running:
    $0 configs ngen --pull-image

  Delete the runtime directory after completion:
    $0 configs ngen --delete-runtime-dir

  Use a different regionalization script:
    $0 configs parreg --script ./rte-scripts/run_region.sh
    $0 configs parreg -s ./rte-scripts/run_region.sh

  Specify walltime for the SLURM job:
    $0 configs ngen --walltime "04:00:00"

  Print the generated SLURM script without submitting:
    $0 configs parreg ngen eval --dry-run

EOF
    exit 0
}


# Handle --help before processing CONFIG_DIR.
if [[ $# -gt 0 && ("$1" == "-h" || "$1" == "--help") ]]; then
    show_help
fi

# CONFIG_DIR is the first argument unless it is a workflow option.
CONFIG_DIR="$(realpath "configs")"

case "${1:-}" in
    parreg|formreg|ngen|eval|"")
        ;;
    -*)
        ;;
    *)
        CONFIG_DIR="$(realpath "$1")"
        shift
        ;;
esac

if [[ ! -d "${CONFIG_DIR}" ]]; then
    echo "ERROR: Config directory '${CONFIG_DIR}' does not exist." >&2
    exit 1
fi
export CONFIG_DIR


while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;

        -i|--image)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: $1 requires a value." >&2
                exit 1
            fi
            IMAGE="$2"
            shift 2
            ;;

        -t|--image-tag)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: $1 requires a value." >&2
                exit 1
            fi
            IMAGE_TAG="$2"
            shift 2
            ;;

        -s|--script)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: $1 requires a value." >&2
                exit 1
            fi
            RUN_REGION_SCRIPT="$2"
            shift 2
            ;;

        -w|--walltime)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: $1 requires a value." >&2
                exit 1
            fi
            WALLTIME="$2"
            shift 2
            ;;

        -p|--pull-image)
            PULL_IMAGE=true
            shift
            ;;

        -d|--delete-runtime-dir)
            DELETE_RUNTIME_DIR=true
            shift
            ;;

        -h|--help)
            show_help
            ;;

        *)
            OPTIONS+=("$1")
            shift
            ;;
    esac
done

# Make sure $RUN_REGION_SCRIPT exists
if [[ ! -f "$RUN_REGION_SCRIPT" ]]; then
    echo "ERROR: Run region script '$RUN_REGION_SCRIPT' does not exist."
    echo "Use the -s or --script to specify the correct path to run_region.sh." >&2
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

OPTION_FLAGS_STR="${OPTION_FLAGS[*]}"

# Determine total number of tasks (n_procs).
NTASKS=$(sed -n 's/^[[:space:]]*n_procs:[[:space:]]*\([^#]*\).*$/\1/p' \
    "${CONFIG_DIR}/config_general.yaml" | tr -d '[:space:]')

if grep -Eq '^[[:space:]]*n_procs:' "${CONFIG_DIR}/config_general.yaml"; then
    if [[ -z "$NTASKS" || ! "$NTASKS" =~ ^[0-9]+$ ]]; then
        echo "ERROR: Invalid n_procs ($NTASKS) in '${CONFIG_DIR}/config_general.yaml'." >&2
        exit 1
    fi
else
    echo "INFO: n_procs not specified in '${CONFIG_DIR}/config_general.yaml'. Using default of 1." >&2
    NTASKS=1
fi

NTASKS=$(( NTASKS < 1 ? 1 : NTASKS ))

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

"${RUN_REGION_SCRIPT}" ${OPTION_FLAGS_STR} -c "${CONFIG_DIR}" --image "${IMAGE}" --image-tag "${IMAGE_TAG}"
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
