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
## 
##     1. First cd to working directory, e.g., /ngen-oe/$USER/run_region, /ngen-dev/$USER/run_region, or ~/run_region.
##     2. Copy sample configs (nwm-region-mgr/configs) to working directory and edit as needed. You can also use the sample configs directly for testing purposes.
##     3. Then run one of the following commands depending on your setup:
##          /ngencerf-app/nwm-rte/sbatch_run_region.sh CONFIG_DIR [OPTIONS] [--dry-run]
##          ~/ngwpc/nwm-rte/sbatch_run_region.sh CONFIG_DIR [OPTIONS] [--dry-run]
## 
## Has 2 positional arguments and some named arguments.
## 
# Arguments:
## 
## \option CONFIG_DIR
## (required) Directory containing configuration YAML files
## \option OPTIONS
## (optional, default: `"parreg"`) Workflow steps to runs: parreg, formreg, ngen, or eval
## \option --dry-run
## (optional switch) If provided, print the generated SLURM script instead of submitting
## \option --image-tag TAG
## (optional, default: `"latest"`) Docker image tag to use for the RTE
## \option --pull-image
## (optional switch) Pull the latest Docker image before running
## \option --delete-runtime-dir
## (optional switch) Delete runtime directory after completion
#
# Examples:
## \example Do a dry-run to see the generated SLURM script without submitting
## \example-code bash
## ~/ngwpc/nwm-rte/sbatch_run_region.sh ~/ngwpc/nwm-region-mgr/configs parreg ngen eval --dry-run
## /ngencerf-app/nwm-rte/sbatch_run_region.sh configs parreg ngen eval --dry-run
## 
## \example Submit parameter regionalization
## \example-code bash
## /ngencerf-app/nwm-rte/sbatch_run_region.sh configs parreg
## /ngencerf-app/nwm-rte/sbatch_run_region.sh configs
## 
## \example Submit formulation regionalization only
## \example-code bash
## /ngencerf-app/nwm-rte/sbatch_run_region.sh configs formreg
## 
## \example Submit NGEN simulation with a different config directory
## \example-code bash
## /ngencerf-app/nwm-rte/sbatch_run_region.sh /ngen-oe/$USER/myconfigs ngen
## 
## \example Submit evaluation only
## \example-code bash
## /ngencerf-app/nwm-rte/sbatch_run_region.sh configs eval
## 
## \example Using an RTE image tag other than 'latest'
## \example-code bash
## /ngencerf-app/nwm-rte/sbatch_run_region.sh configs ngen --image-tag "069ad0f6d332"
## 
## \example Pull the latest RTE image before running
## \example-code bash
## /ngencerf-app/nwm-rte/sbatch_run_region.sh configs ngen --pull-image
## 
## \example Delete runtime directory after completion (default is to keep it for debugging)
## \example-code bash
## /ngencerf-app/nwm-rte/sbatch_run_region.sh configs ngen --pull-image --delete-runtime-dir
## 
# -----------------------------------------------------------------------------

# determine parent dir of current run script (assuming run_region.sh is also located here)
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# ensure run_region.sh exists in script_dir
if [[ ! -f "${SCRIPT_DIR}/run_region.sh" ]]; then
  echo "ERROR: Could not find run_region.sh in ${SCRIPT_DIR}. run_region.sh should exist in the same directory as $(realpath "$0")" >&2
  exit 1
fi

# config_dir is the first argument ONLY if it is not an option
if [[ $# -gt 0 && "$1" != -* ]]; then
  CONFIG_DIR="$(realpath "$1")"
  shift
else
  CONFIG_DIR="$(realpath "configs")"
fi

# ensure config_dir exists
if [[ ! -d "${CONFIG_DIR}" ]]; then
  echo "ERROR: Config directory '${CONFIG_DIR}' does not exist." >&2
  exit 1
fi
export CONFIG_DIR

# determine options to run from the remaining arguments
OPTIONS=()
DRY_RUN=false
IMAGE_TAG="latest"
PULL_IMAGE=false
DELETE_RUNTIME_DIR=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --image-tag)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --image-tag requires a value." >&2
        exit 1
      fi
      IMAGE_TAG="$2"
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
    *)
      OPTIONS+=("$1")
      shift
      ;;
  esac
done


# Default option
if [[ ${#OPTIONS[@]} -eq 0 ]]; then
  OPTIONS=("parreg")
fi

# Validate options
VALID_OPTIONS=(formreg parreg ngen eval)
for opt in "${OPTIONS[@]}"; do
  if [[ ! " ${VALID_OPTIONS[*]} " =~ " ${opt} " ]]; then
    echo "ERROR: Invalid option '${opt}'. Valid options: ${VALID_OPTIONS[*]}"
    exit 1
  fi
done

# Sort options in canonical order
SORTED_OPTIONS=()
for valid in "${VALID_OPTIONS[@]}"; do
  for opt in "${OPTIONS[@]}"; do
    [[ "$opt" == "$valid" ]] && SORTED_OPTIONS+=("$opt")
  done
done
OPTIONS=("${SORTED_OPTIONS[@]}")

# Build combined option flags
OPTION_FLAGS=()
for opt in "${OPTIONS[@]}"; do
  OPTION_FLAGS+=("--$opt")
done

# Add --pull-image if requested
if $PULL_IMAGE; then
  OPTION_FLAGS+=("--pull-image")
fi

# Add --delete-runtime-dir if requested
if $DELETE_RUNTIME_DIR; then
  OPTION_FLAGS+=("--delete-runtime-dir")
fi

# Determine total number of tasks (n_procs)
read NTASKS <<< $(
python3 - <<'EOF'
import yaml, os
from pathlib import Path

cfg = yaml.safe_load((Path(os.environ["CONFIG_DIR"]) / "config_general.yaml").read_text())
n_procs = int(cfg["general"].get("n_procs", 0))
print(max(n_procs, 1))

EOF
)

# Get all idle nodes and their CPU counts
IDLE_NODES=$(sinfo -h -t idle -N -o "%N %c %P")

# Filter nodes that have at least NTASKS CPUs and sort by CPU count (ascending)
NODE_INFO=$(echo "$IDLE_NODES" | awk -v n="$NTASKS" '$2 >= n {print}' | sort -k2n | head -n1)

# Extract node name, CPU count, and partition
NODE_NAME=$(echo "$NODE_INFO" | awk '{print $1}')
NODE_CPUS=$(echo "$NODE_INFO" | awk '{print $2}')
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
echo "  script_dir    = $SCRIPT_DIR"
echo "  image_tag     = $IMAGE_TAG"
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
#SBATCH --time=240:00:00
#SBATCH --output=logs/region-${JOB_SUFFIX}-%j.log
#SBATCH --error=logs/region-${JOB_SUFFIX}-%j.log

set -euo pipefail

echo "Job started on nodes: \$SLURM_JOB_NODELIST"
echo "Nodes allocated: \$SLURM_JOB_NUM_NODES"
echo "Running on directory: \$SLURM_SUBMIT_DIR"
echo "Job ID: \$SLURM_JOB_ID"

/ngencerf-app/nwm-rte/run_region.sh ${OPTION_FLAGS[@]} -c "${CONFIG_DIR}" --image-tag "${IMAGE_TAG}"
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