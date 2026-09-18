#!/bin/bash
#
# make_coastal_forcing.sh
#
# This was renamed from /run_coastal.sh to /bin_mounted/ngen_rte/coastal/make_coastal_forcing.sh and edited.
#
# This is a script to generate coastal forcing data using the NextGen Forcings Engine as ran through the NextGen RTE build.
#
# NOTE:
#     See repository ``nwm-coastal`` (file ``nwm-coastal/scripts/setup_data_coastal.sh``) for the scripts needed to download / set up input data required to run coastal forcing workflows:
# 
#     These files are masked versions of the full CONUS nc files, masked to an area around the test gage for testing CONUS workflows
#     on a machine that may not have enough RAM for an actual full CONUS run:
#         run_ngen/data/esmf_mesh/NWM/domain/GEOGRID_LDASOUT_Spatial_Metadata_CONUS_debug_gauge_01123000.nc
#         run_ngen/data/esmf_mesh/NWM/domain/geo_em_CONUS_debug_gauge_01123000.nc
#

set -euo pipefail

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
cd "${SCRIPT_DIR}/../../.."
# config.bashrc derives sibling repository paths from the root-level caller.
BASH_ARGV0="${PWD}/$(basename "${BASH_SOURCE[0]}")"
source run.sh

run_name=${1:-"coastal"}

set -x

### CONUS subset (small spatial mask) for quick/debug runs using the CONUS logic.
docker_run python -um ngen_rte.coastal.make_coastal_forcing --cycle_datetime "2025-09-15 00:00:00" -rname "${run_name}_debug_standard_ana" --forcing_configuration standard_ana --global_domain CONUS --debug_conus_subset
# docker_run python -um ngen_rte.coastal.make_coastal_forcing --cycle_datetime "2025-09-15 00:00:00" -rname "${run_name}_debug_short_range" --forcing_configuration short_range --global_domain CONUS --debug_conus_subset
# docker_run python -um ngen_rte.coastal.make_coastal_forcing --cycle_datetime "2025-09-15 00:00:00" -rname "${run_name}_debug_aorc" --forcing_configuration aorc --global_domain CONUS --debug_conus_subset
# docker_run python -um ngen_rte.coastal.make_coastal_forcing --cycle_datetime "2025-09-15 00:00:00" -rname "${run_name}_debug_extended_ana" --forcing_configuration extended_ana --global_domain CONUS --debug_conus_subset

## Warmup
# docker_run python -um ngen_rte.coastal.make_coastal_forcing --cycle_datetime "2025-09-15 00:00:00" -rname "${run_name}_debug_standard_ana_warmup" --forcing_configuration standard_ana --global_domain CONUS --warm_weights --debug_conus_subset
## Actual run
# docker_run python -um ngen_rte.coastal.make_coastal_forcing --cycle_datetime "2025-09-15 00:00:00" -rname "${run_name}_debug_standard_ana_warmed" --forcing_configuration standard_ana --global_domain CONUS --debug_conus_subset

## Analysis timing overrides: retain a four-hour lookback window while processing two hourly updates.
# docker_run python -um ngen_rte.coastal.make_coastal_forcing --cycle_datetime "2025-09-15 00:00:00" -rname "${run_name}_debug_standard_ana_timing" --forcing_configuration standard_ana --global_domain CONUS --lookback 240 --forecast_input_horizons 120 --debug_conus_subset


##############################################
### FULL CONUS - REQUIRES LOTS OF MEMORY
##############################################

### Warmup the reusable weights first (one product at a time in series) for scalability. Each configured product is processed in its own subprocess, reducing peak memory during the subsequent forcing run.
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -fconfig standard_ana -gdomain CONUS --warm_weights
### Actual run
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_standard_ana" -fconfig standard_ana -gdomain CONUS

### Actual runs without warming
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_aorc" -fconfig aorc -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_cold_start" -fconfig cold_start -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_extended_ana" -fconfig extended_ana -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_long_range_ana" -fconfig long_range_ana -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_long_range_mem1" -fconfig long_range_mem1 -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_long_range_mem2" -fconfig long_range_mem2 -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_long_range_mem3" -fconfig long_range_mem3 -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_long_range_mem4" -fconfig long_range_mem4 -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_blend" -fconfig medium_range_blend -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem1" -fconfig medium_range_mem1 -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem2" -fconfig medium_range_mem2 -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem3" -fconfig medium_range_mem3 -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem4" -fconfig medium_range_mem4 -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem5" -fconfig medium_range_mem5 -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem6" -fconfig medium_range_mem6 -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem_no_da" -fconfig medium_range_no_da -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_nwm" -fconfig nwm -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_short_range" -fconfig short_range -gdomain CONUS
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_standard_ana" -fconfig standard_ana -gdomain CONUS


##############################################
### Alaska
##############################################

# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_cold_start_alaska" -fconfig cold_start_alaska -gdomain Alaska
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_extended_ana_alaska" -fconfig extended_ana_alaska -gdomain Alaska
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_blend_alaska" -fconfig medium_range_blend_alaska -gdomain Alaska
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_short_range_alaska" -fconfig short_range_alaska -gdomain Alaska
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_short_range_extended_alaska" -fconfig short_range_extended_alaska -gdomain Alaska
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_standard_ana_alaska" -fconfig standard_ana_alaska -gdomain Alaska


##############################################
### Hawaii
##############################################

# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_cold_start_hi" -fconfig cold_start_hawaii -gdomain Hawaii
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_short_range_hawaii" -fconfig short_range_hawaii -gdomain Hawaii
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_standard_ana_hawaii" -fconfig standard_ana_hawaii -gdomain Hawaii
### TODO delete me
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2026-08-01 00:00:00" -rname "${run_name}_standard_ana_hawaii" -fconfig standard_ana_hawaii -gdomain Hawaii


##############################################
### Puerto Rico
##############################################

## Warmup
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -fconfig standard_ana_puertorico -gdomain Puerto_Rico --warm_weights
## Actual run
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_cold_start_puertorico" -fconfig cold_start_puertorico -gdomain Puerto_Rico
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_short_range_puertorico" -fconfig short_range_puertorico -gdomain Puerto_Rico
# docker_run python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -rname "${run_name}_standard_ana_puertorico" -fconfig standard_ana_puertorico -gdomain Puerto_Rico

echo "Finished ${0}"
exit 0
