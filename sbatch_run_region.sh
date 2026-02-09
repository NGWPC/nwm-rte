#!/bin/bash
set -euo pipefail

# -----------------------------------------------------------------------------
# sbatch_run_region.sh
#
# Submits the regionalization workflow to SLURM using sbatch.
#
# Usage:
#   # First cd to working directory, e.g., /ngen-oe/$USER/run_region, /ngen-dev/$USER/run_region, or ~/run_region.
#   # Copy sample configs (nwm-region-mgr/configs) to working directory and edit as needed. You can also use the 
#   # sample configs directly for testing purposes.
#   # Then run one of the following commands depending on your setup:
#
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh CONFIG_DIR [OPTIONS] [--dry-run]
#   ~/ngwpc/nwm-rte/sbatch_run_region.sh CONFIG_DIR [OPTIONS] [--dry-run]
#
# Arguments:
#   CONFIG_DIR : Directory containing configuration YAML files (required)
#   OPTIONS    : Workflow steps to runs: parreg, formreg, ngen, or eval (optional, default: parreg)
#   --dry-run  : If provided, print the generated SLURM script instead of submitting (optional)
#
# Examples:
#   # Do a dry-run to see the generated SLURM script without submitting
#   ~/ngwpc/nwm-rte/sbatch_run_region.sh ~/ngwpc/nwm-region-mgr/configs parreg ngen eval --dry-run
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh configs parreg ngen eval --dry-run
#
#   # Submit parameter regionalization
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh configs parreg
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh configs
#
#   # Submit formulation regionalization only
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh configs formreg
#
#   # Submit NGEN simulation with a different config directory
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh /ngen-oe/$USER/myconfigs ngen
#
#   # Submit evaluation only
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh configs eval
#
# -----------------------------------------------------------------------------

# determine parent dir of current run script (assuming run_region.sh is also located here)
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# ensure run_region.sh exists in script_dir
if [[ ! -f "${SCRIPT_DIR}/run_region.sh" ]]; then
  echo "ERROR: Could not find run_region.sh in ${SCRIPT_DIR}. run_region.sh should exist in the same directory as $(realpath "$0")" >&2
  exit 1
fi

# config_dir is the first argument
CONFIG_DIR="$(realpath "${1:-configs}")"
shift

# ensure config_dir exists
if [[ ! -d "${CONFIG_DIR}" ]]; then
  echo "ERROR: Config directory '${CONFIG_DIR}' does not exist." >&2
  exit 1
fi
export CONFIG_DIR

# determine options to run from the remaining arguments
OPTIONS=()
DRY_RUN=false

for arg in "$@"; do
  if [[ "$arg" == "--dry-run" ]]; then
    DRY_RUN=true
  else
    OPTIONS+=("$arg")
  fi
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

# Determine SLURM resources
read NODES NTASKS CPUS_PER_TASK <<< $(
python3 - <<'EOF'
import math, yaml, os
from pathlib import Path

cfg = yaml.safe_load((Path(os.environ["CONFIG_DIR"]) / "config_general.yaml").read_text())

n_procs = int(cfg["general"].get("n_procs", 0))
cores_per_node = int(os.environ.get("CORES_PER_NODE", 36))

if n_procs <= 0:
    n_procs = cores_per_node

print(math.ceil(n_procs / cores_per_node), n_procs, 1)
EOF
)

# Build combined option flags
OPTION_FLAGS=()
for opt in "${OPTIONS[@]}"; do
  OPTION_FLAGS+=("--$opt")
done

JOB_SUFFIX=$(IFS=-; echo "${OPTIONS[*]}")

echo "Submitting job:"
echo "  options      = ${OPTIONS[*]}"
echo "  nodes        = $NODES"
echo "  ntasks       = $NTASKS"
echo "  cpus         = $CPUS_PER_TASK"
echo "  config_dir   = $CONFIG_DIR"
echo "  script_dir   = $SCRIPT_DIR"
echo

SBATCH_SCRIPT=$(cat <<EOF
#!/bin/bash
#SBATCH --job-name=region-${JOB_SUFFIX}
#SBATCH --nodes=${NODES}
#SBATCH --ntasks=${NTASKS}
#SBATCH --cpus-per-task=${CPUS_PER_TASK}
#SBATCH --time=240:00:00
#SBATCH --output=region-${JOB_SUFFIX}-%j.log
#SBATCH --error=region-${JOB_SUFFIX}-%j.log

set -euo pipefail

echo "Job started on nodes: \$SLURM_JOB_NODELIST"
echo "Nodes allocated: \$SLURM_JOB_NUM_NODES"
echo "Running on directory: \$SLURM_SUBMIT_DIR"
echo "Job ID: \$SLURM_JOB_ID"

/ngencerf-app/nwm-rte/run_region.sh ${OPTION_FLAGS[*]} -c "${CONFIG_DIR}"

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