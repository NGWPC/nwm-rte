#!/bin/bash

set -euo pipefail

source config.bashrc

function write_python_cli_help_txt () {
    python_script_basename="${1}"
    python_script_path="/ngen-app/bin/bin_mounted/${python_script_basename}"
    output_file="docs/reference/python_cli_help__${python_script_basename}.txt"
    echo "Calling --help on script ${python_script_path} to write: ${output_file}"

    sudo docker run --entrypoint python \
        -v "$(pwd)/bin_mounted/:/ngen-app/bin/bin_mounted/" \
        --rm ${TARGET_IMAGE_NAME} \
        "${python_script_path}" --help > "${output_file}"
}

for bn in "run_default.py" "run_calibration.py" "run_forecast.py" "run_tests.py" "run_regionalization.py"; do
    write_python_cli_help_txt "${bn}"
done
