#!/bin/bash
# 
# ngen_rte_run.sh
# 
# This script makes a docker run call to execute a regionalization workflow in the RTE Docker image (already built).
# 
# Steps before running this script:
#   1. Set up local workspace: clone sibling Git repositories and download data following instructions in the RTE readme.
#   2. Build a local docker image using ./ngen_rte_build.sh.
#   3. Review the CLI args of this script.
# 

set -euo pipefail
set -x

source config.bashrc

function docker_run {
    time sudo docker run --entrypoint python \
        -v "${MNT__RUN_NGEN__HOST}:${MNT__RUN_NGEN__CONTAINER}" \
        -v "${MNT__S3_DATA__HOST}:${MNT__S3_DATA__CONTAINER}" \
        -v "${RUN_NGEN_ROOT__HOST}/data/esmf_mesh/:/ngen-app/data/esmf_mesh/" \
        -v "${RUN_NGEN_ROOT__HOST}/data/scratch:/ngen-app/data/scratch" \
        -v "$(pwd)/docker_logs/run:/ngencerf/data/run-logs" \
        -v "$(pwd)/bin_mounted/:/ngen-app/bin/bin_mounted/" \
        \
        -v "${REPOS_COMMON_ROOT__HOST}/nwm-region-mgr:/ngen-app/nwm-region-mgr" \
        -v "${REPOS_COMMON_ROOT__HOST}/nwm-eval-mgr/data:/ngen-app/nwm-eval-mgr/data" \
        \
        --rm ${TARGET_IMAGE_NAME} "$@"
}

## Parse command line arguments
OPTIND=1
parreg=false
formreg=false
ngen=false
eval=false
ARGS=$(getopt -o pfneh --long parreg,formreg,ngen,eval,help -- "$@")

if [ $? != 0 ] ; then echo "Failed parsing options." >&2 ; exit 1 ; fi
eval set -- "$ARGS"

while true; do
    case "$1" in
        -p|--parreg) parreg=true # run parameter regionalization (which also includes formulation regionalization)
            shift;;
        -f|--formreg) formreg=true # run formulation regionalization only
            shift;;
        -n|--ngen) ngen=true # run ngen simulation
            shift;;
        -e|--eval) eval=true # run evaluation
            shift;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]

        Options:
        -p,  --parreg             Run the parameter regionalization workflow (which also includes formulation regionalization)
        -f,  --formreg            Run formulation regionalization only
        -n,  --ngen               Run the NGEN model workflow
        -e,  --eval               Run the evaluation workflow

        -h,  --help               Show this help message and exit
        " >&2
            exit 0
            ;;
        --) shift; break ;;
        *) echo "Internal error!" ; exit 1 ;;
    esac
done


# docker_run
if [ "$parreg" = true ] ; then
    docker_run "/ngen-app/bin/bin_mounted/run_regionalization.py" --parreg
fi
if [ "$formreg" = true ] ; then
    docker_run "/ngen-app/bin/bin_mounted/run_regionalization.py" --formreg
fi
if [ "$ngen" = true ] ; then
    docker_run "/ngen-app/bin/bin_mounted/run_regionalization.py" --ngen
fi
if [ "$eval" = true ] ; then
    docker_run "/ngen-app/bin/bin_mounted/run_regionalization.py" --eval
fi
if [ "$parreg" = false ] && [ "$formreg" = false ] && [ "$ngen" = false ] && [ "$eval" = false ] ; then
    fatal "No workflow specified to run. Use -h or --help for usage information."
fi


exit 0
