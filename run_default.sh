#!/bin/bash
### Example commands for running default realizations

set -euo pipefail

source run.sh

set -x

sudo rm -rf ~/ngwpc/run_ngen/default/test_bmi/01123000


### Short Range
docker_run python "/ngen-app/bin/bin_mounted/run_default.py" -n 2 -fconfig "short_range" -dt "2026-03-30 06:00:00" -rname "default_sr"
### Analysis & Assimilation
docker_run python "/ngen-app/bin/bin_mounted/run_default.py" -n 2 -fconfig "standard_ana" -dt "2026-03-30 06:00:00" -rname "default_ana"
### Medium Range
docker_run python "/ngen-app/bin/bin_mounted/run_default.py" -n 2 -fconfig "medium_range_blend" -dt "2026-03-30 06:00:00" -rname "default_mr"

### Historical / Retrospective Forcing
docker_run python "/ngen-app/bin/bin_mounted/run_default.py" -n 2 -fconfig "aorc" -dt "2013-07-25 00:00:00" -dur 2 -rname "default_aorc"
docker_run python "/ngen-app/bin/bin_mounted/run_default.py" -n 2 -fconfig "nwm" -dt "2013-07-25 00:00:00" -dur 2 -rname "default_nwm"

exit 0
