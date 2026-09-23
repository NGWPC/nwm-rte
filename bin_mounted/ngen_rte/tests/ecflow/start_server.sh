#!/bin/bash
# 
# Start the ecflow server in a detached Docker container.
# 
# This must be ran before running run_test_ecf_task_mgr.sh.
# 
# Run from nwm-rte repo root: ./bin_mounted/ngen_rte/tests/ecflow/start_server.sh
# 

set -euo pipefail

NWM_PACKAGE_DIR="${NWM_PACKAGE_DIR:=$(cd "../nextgen-support-scripts/nwm.v4.0.0" && pwd)}"
DATAROOT="${DATAROOT:-${HOME}/ngwpc/run_ngen}"
COMROOT="${COMROOT:-${DATAROOT}/com}"
DBNROOT="${DBNROOT:-${DATAROOT}/dbn}"
DCOMROOT="${DCOMROOT:-${DATAROOT}/dcom}"
ECF_PORT="${ECF_PORT:-3141}"

export NWM_PACKAGE_DIR DATAROOT COMROOT DBNROOT DCOMROOT ECF_PORT

( cd ../nextgen-support-scripts/nwm.v4.0.0/ecflow-server && ./ecflow-server-docker-build.sh no )
( cd ../nextgen-support-scripts/nwm.v4.0.0/ecflow-server && ./ecflow-server-start.sh )
