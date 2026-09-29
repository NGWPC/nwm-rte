# Shell Reference

## Configuration

::: config.bashrc
    handler: shell

## Setup

::: setup_clone_repos.sh
    handler: shell

::: setup_data.sh
    handler: shell

::: setup_data_one_gage.sh
    handler: shell

## Build

::: ngen_rte_build.sh
    handler: shell

## Run `pytest` Without Dev Container

See also: [Steps to Run: pytest](../user-guide/get-started.md#pytest)

::: ./run_test_pytest.sh
    handler: shell

## Enter the Container Interactively

::: run.sh
    handler: shell

## Run Forecasts and Calibrations

::: run_default.sh
    handler: shell

::: run_calib.sh
    handler: shell

::: run_fcst.sh
    handler: shell

::: run_suite.sh
    handler: shell

::: run_test_formulations.sh
    handler: shell

::: run_region_standalone.sh
    handler: shell

## Run Output Postprocessing

For complete workflow documentation, see the `nwm-data-assimilation` repository.

::: run_output_postprocess.sh
    handler: shell

::: run_output_mosaic.sh
    handler: shell

## Coastal Forcing

For complete coastal workflow documentation, see the `nwm-coastal` repository.

::: bin_mounted/ngen_rte/coastal/make_coastal_forcing.sh
    handler: shell

## Additional Utilities

::: install_debuggers.sh
    handler: shell

::: install_package.sh
    handler: shell


## Run Regionalization Workflows

For more information, see the `nwm-region-mgr` repository.

::: run_region.sh
    handler: shell

::: sbatch_run_region.sh
    handler: shell
