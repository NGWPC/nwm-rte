#!/bin/bash

set -euo pipefail
source run.sh

##
## \brief
## Example commands for running coastal forcing realizations. See CLI args for [`run_coastal.py`].
##
## \desc
## Runs the NWM forcing engine in gridded output mode, producing netCDF forcing
## files suitable for coastal models. Does not require a gage or catchment.
##
## Timing can be specified via:
##   -dt (operational forecasts: start/end derived automatically)
##   -start / -end (retrospective/AORC: explicit time window)
##
## Any existing forcing configuration template can be used with the matching domain, e.g.:
##   CONUS:       short_range, medium_range_blend, extended_ana, standard_ana, aorc
##   Alaska:      short_range_alaska, medium_range_blend_alaska, standard_ana_alaska
##   Hawaii:      cold_start_hawaii, short_range_hawaii, standard_ana_hawaii
##   Puerto Rico: cold_start_puertorico, short_range_puertorico, standard_ana_puertorico
## Available forcing config options are in ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/
##
## Output is written to:
##   /ngen-app/data/scratch/<forcing_configuration>_coastal/<global_domain>_<b_date>.nc
##
## \option run_name
## Optional. Default="coastal".
##
## \usage ./run_coastal.sh
##

# Default to coastal_, override via CLI arg
run_name=${1:-"coastal"}

set -x

# docker_run python -um "ngen_rte.run_coastal" --help


#Operational Configurations

# CONUS - REQUIRES LOTS OF MEMORY TO SUCCESSFULLY RUN
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_aorc" -fconfig aorc -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_cold_start" -fconfig cold_start -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_extended_ana" -fconfig extended_ana -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_long_range_ana" -fconfig long_range_ana -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_long_range_mem1" -fconfig long_range_mem1 -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_long_range_mem2" -fconfig long_range_mem2 -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_long_range_mem3" -fconfig long_range_mem3 -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_long_range_mem4" -fconfig long_range_mem4 -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_blend" -fconfig medium_range_blend -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem1" -fconfig medium_range_mem1 -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem2" -fconfig medium_range_mem2 -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem3" -fconfig medium_range_mem3 -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem4" -fconfig medium_range_mem4 -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem5" -fconfig medium_range_mem5 -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem6" -fconfig medium_range_mem6 -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_mem_no_da" -fconfig medium_range_no_da -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_nwm" -fconfig nwm -gdomain CONUS
docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_short_range" -fconfig short_range -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_standard_ana" -fconfig standard_ana -gdomain CONUS

# Alaska
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_cold_start_alaska" -fconfig cold_start_alaska -gdomain Alaska
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_extended_ana_alaska" -fconfig extended_ana_alaska -gdomain Alaska
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_medium_range_blend_alaska" -fconfig medium_range_blend_alaska -gdomain Alaska
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_short_range_alaska" -fconfig short_range_alaska -gdomain Alaska
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_short_range_extended_alaska" -fconfig short_range_extended_alaska -gdomain Alaska
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_standard_ana_alaska" -fconfig standard_ana_alaska -gdomain Alaska

# Hawaii
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_cold_start_hi" -fconfig cold_start_hawaii -gdomain Hawaii
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_short_range_hawaii" -fconfig short_range_hawaii -gdomain Hawaii
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_standard_ana_hawaii" -fconfig standard_ana_hawaii -gdomain Hawaii

# Puerto Rico
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_cold_start_puertorico" -fconfig cold_start_puertorico -gdomain Puerto_Rico
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_short_range_puertorico" -fconfig short_range_puertorico -gdomain Puerto_Rico
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_standard_ana_puertorico" -fconfig standard_ana_puertorico -gdomain Puerto_Rico

exit 0
