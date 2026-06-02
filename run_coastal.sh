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
## Any existing forcing configuration template can be used with the matching domain:
##   CONUS:       short_range, medium_range_blend, extended_ana, standard_ana, aorc
##   Alaska:      short_range_alaska, medium_range_blend_alaska, standard_ana_alaska
##   Hawaii:      cold_start_hawaii, standard_ana_hawaii
##   Puerto Rico: short_range_puertorico, standard_ana_puertorico, cold_start_puertorico
##
## Output is written to:
##   /ngen-app/data/scratch/<forcing_configuration>_coastal/<global_domain>_<b_date>.nc
##
## \option run_name
## Optional. Default="coastal_run1".
##
## \usage ./run_coastal.sh
##

# Default to coastal_, override via CLI arg
run_name=${1:-"coastal_run1"}

set -x

# docker_run python -um "ngen_rte.run_coastal" --help

# TODO: Retrospective (AORC) Configurations

#Operational Configurations

# CONUS - Operational
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_short" -fconfig short_range -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_ana" -fconfig standard_ana -gdomain CONUS
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_mr" -fconfig medium_range_blend -gdomain CONUS

# Alaska
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_short_ak" -fconfig short_range_alaska -gdomain Alaska

# Hawaii
docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_hi" -fconfig cold_start_hawaii -gdomain Hawaii

# Puerto Rico
# docker_run python -um "ngen_rte.run_coastal" -dt "2025-09-15 00:00:00" -rname "${run_name}_prvi" -fconfig short_range_puertorico -gdomain Puerto_Rico

exit 0
