#!/bin/bash

set -euo pipefail

source config.bashrc

function write_python_cli_help_txt () {
    module="${1}"
    module_basename="${module##*.}"
    output_file="docs/reference/python_cli_help__${module_basename}.py.txt"
    echo "Calling --help on module ${module} to write: ${output_file}"

    sudo docker run --entrypoint python \
        -v "$(pwd)/bin_mounted/:/ngen-app/bin/bin_mounted/" \
        -w "/ngen-app/bin/bin_mounted/" \
        -v "$(pwd)/docs/reference/:/docs/reference/" \
        --rm ${TARGET_IMAGE_NAME} \
        -um "${module}" --help > "${output_file}"
}

for module in "ngen_rte.run_default" "ngen_rte.run_calibration" "ngen_rte.run_forecast" "ngen_rte.tests.run_tests" "ngen_rte.run_regionalization"; do
    write_python_cli_help_txt "${module}"
done
