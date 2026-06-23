#!/bin/bash
# 
# Test the interactions of RTE with the ecFlow server.
# 
# Sequence: 
#   1. Run the pytest of the ecf_task_mgr Python package to confirm it is installed and can connect to the server.
#       Note that this step also initializes the Subtask variables on the server, so it must be ran at least once before running the other steps.
#   2. Run a subtask (RTE call) that should succeed, then dump its ecFlow metadata to disk.
#   3. Run a subtask (RTE call) that should fail, then dump its ecFlow metadata to disk.
# 
# To inspect the dumped ecFlow metadata on the host disk, see run.sh for how the container mounts to its /tmp/.
# 
# Usage:
#   1. Start the ecflow server:
#       ./bin_mounted/ngen_rte/tests/ecflow/start_server.sh
#   2. Run this script from the nwm-rte repo root:
#       ./run_test_ecf_task_mgr.sh
# 

set -euo pipefail

source run.sh

# This pytest confirms that the ecf_task_mgr package is installed and can connect to the server.
# It also initializes the Subtask variables on the server, so it must be ran at least once before running the other steps.
docker_run pytest --pyargs ecf_task_mgr.tests

ECF_TASK="/nwm/hourly/nwm_analysis_assim/jnwm_conus_analysis_assim"
ECF_SUBTASK="no_subtask_type__20260615_120000_000000__gage__01123000"
TEST_HYDROFAB_FILE="/ngen-app/bin/ngen_rte/tests/test_data/gauge_01123000.gpkg"
ECFLOW_TMP_OUT_ROOT="/tmp/ecf_dump/$(date +%Y%m%d_%H%M%S)"


# clear_previous: delete files from earlier run and re-set ecFlow (Sub)task variables to empty string.
function clear_previous() {
    sudo rm -rf ../run_ngen/default/test_bmi/01123000
    ecflow_client --alter=change variable "${ECF_SUBTASK}_status" "" "${ECF_TASK}"
    ecflow_client --alter=change variable "${ECF_SUBTASK}_info" "" "${ECF_TASK}"
}


############################
##### Success Reaction #####
# Attempt a RTE subtask call that should *succeed*,
# then call ``dump_ecf_vars.py`` to simulate a mock reaction. In this case, just fetch, parse, and dump its metadata.
clear_previous

# Attempt call that should succeed. Don't include `|| true` (want to stop if it fails).
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "standard_ana" -dt "2026-06-15 12:00:00" -rname "default_ana" --gage_id 01123000 --hydrofab_file "${TEST_HYDROFAB_FILE}" \
    --ecf-task="${ECF_TASK}" \
    --ecf-subtask="${ECF_SUBTASK}"

# Inspect and dump task metadata from ecFlow
docker_run python /ngen-app/bin/ngen_rte/tests/ecflow/dump_ecf_vars.py \
    --ecf-task="${ECF_TASK}" \
    --ecf-subtask="${ECF_SUBTASK}" \
    --outdir="${ECFLOW_TMP_OUT_ROOT}/should_succeed"

# docker_run cat "${ECFLOW_TMP_OUT_ROOT}/should_succeed/${ECF_SUBTASK}_status.json"
# docker_run cat "${ECFLOW_TMP_OUT_ROOT}/should_succeed/${ECF_SUBTASK}_info.json"


#########################
##### Fail Reaction #####
# Attempt a RTE subtask call that should *fail*,
# then call ``dump_ecf_vars.py`` to simulate a mock reaction. In this case, just fetch, parse, and dump its metadata.
clear_previous

# Attempt call that should fail. Do include `|| true` (want to continue when it fails).
docker_run python -um "ngen_rte.run_default" -n 2 -fconfig "standard_ana" -dt "2026-06-15 12:00:00" -rname "default_ana" --gage_id 01123000 --hydrofab_file "/does/not/exist.gpkg" \
    --ecf-task="${ECF_TASK}" \
    --ecf-subtask="${ECF_SUBTASK}" \
    || true

# Inspect and dump task metadata from ecFlow
docker_run python /ngen-app/bin/ngen_rte/tests/ecflow/dump_ecf_vars.py \
    --ecf-task="${ECF_TASK}" \
    --ecf-subtask="${ECF_SUBTASK}" \
    --outdir="${ECFLOW_TMP_OUT_ROOT}/should_fail"

# docker_run cat "${ECFLOW_TMP_OUT_ROOT}/should_fail/${ECF_SUBTASK}_status.json"
# docker_run cat "${ECFLOW_TMP_OUT_ROOT}/should_fail/${ECF_SUBTASK}_info.json"
