#!/bin/bash
set -euo pipefail

# -----------------------------------------------------------------------------
# sbatch_run_region.sh
#
# Submits the regionalization workflow to SLURM using sbatch.
#
# Usage:
#   cd [working_directory, e.g., /ngen-oe/$USER/run_region, /ngen-dev/$USER/run_region, or ~/run_region]
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh CONFIG_DIR OPTION [--dry-run]
#
# Examples:
#   # Submit parameter regionalization with default configs
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh configs parreg
#
#   # Submit formulation regionalization only
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh configs formreg
#
#   # Submit NGEN simulation with a different config directory
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh /ngen-oe/$USER/myconfigs ngen
#
#   # Do a dry-run to see the generated SLURM script without submitting
#   /ngencerf-app/nwm-rte/sbatch_run_region.sh configs parreg --dry-run
#
# Arguments:
#   CONFIG_DIR : Directory containing configuration YAML files (required)
#   OPTION     : Workflow step to run: parreg, formreg, ngen, or eval (required)
#   --dry-run  : If provided, print the generated SLURM script instead of submitting (optional)
# -----------------------------------------------------------------------------

CONFIG_DIR="$(realpath "${1:-configs}")"
OPTION="${2:-parreg}"   

# determine parent dir of current run script (assuming run_region.sh is also located here)
SCRIPT_DIR="$(dirname "$(realpath "$0")")"

# Determine number of nodes and tasks from YAML
read NODES NTASKS CPUS_PER_TASK <<< $(
python3 - <<'EOF'
import math
import yaml
from pathlib import Path
import os, sys

config_dir = Path(os.environ.get("CONFIG_DIR", "configs"))
cfg = yaml.safe_load((config_dir / "config_general.yaml").read_text())

n_procs = int(cfg["general"]["n_procs"])

# Get number of cores per node from environment or default to 36
cores_per_node = int(os.environ.get("CORES_PER_NODE", 36))

if n_procs <= 0:
    n_procs = cores_per_node

nodes = math.ceil(n_procs / cores_per_node)
ntasks = n_procs
cpus_per_task = 1

print(nodes, ntasks, cpus_per_task)
EOF
)

echo "Submitting job:"
echo "  option  = $OPTION"
echo "  nodes   = $NODES"
echo "  ntasks  = $NTASKS"
echo "  cpus    = $CPUS_PER_TASK"
echo "  config_dir = $CONFIG_DIR"
echo "  script_dir = $SCRIPT_DIR"

SBATCH_SCRIPT=$(cat <<EOF
#!/bin/bash
#SBATCH --job-name=region-${OPTION}
#SBATCH --nodes=${NODES}
#SBATCH --ntasks=${NTASKS}
#SBATCH --cpus-per-task=${CPUS_PER_TASK}
#SBATCH --time=240:00:00
#SBATCH --output=region-${OPTION}-%j.out
#SBATCH --error=region-${OPTION}-%j.err

set -euo pipefail

echo "Job started on nodes: \$SLURM_JOB_NODELIST"
echo "Nodes allocated: \$SLURM_JOB_NUM_NODES"
echo "Running on directory: \$SLURM_SUBMIT_DIR"
echo "Job ID: \$SLURM_JOB_ID"

cd "\$SCRIPT_DIR"
./run_region.sh --${OPTION} -c "${CONFIG_DIR}"
EOF
)

echo "===== sbatch script ====="
echo "$SBATCH_SCRIPT"
echo "========================="

# If dry run, exit
if [[ "${3:-}" == "--dry-run" ]]; then
    echo "DRY RUN"
    exit 0
fi

# Submit the job
echo "$SBATCH_SCRIPT" | sbatch
echo "Job submitted."