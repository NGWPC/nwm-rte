# Auxilliary Workflows

## Regionalization

The full regionalization workflow generates formulation and parameter assignments through `nwm-region-mgr`. RTE provides [`run_region.sh`](../reference/shell.md#run_region.sh), [`run_regionalization.py`](../reference/python.md#regionalization-workflows), and [`sbatch_run_region.sh`](../reference/shell.md#sbatch_run_region.sh) as execution wrappers for that workflow.

For workflow configuration, outputs, and Slurm guidance, see the documentation of the `nwm-region-mgr` repository.

### Standalone Regionalized Forecasts

[`run_region_standalone.sh`](../reference/shell.md#run_region_standalone.sh) and [`run_regionalization_standalone.py`](../reference/python.md#run_regionalization_standalonepy) do not generate regionalization parameters. They run an ngen forecast for a gage or VPU using formulation assignments, catchment groups, and parameters produced by a previously completed regionalization workflow.

### Caveats for Regionalization Workflows

At runtime, host disk mounts occur within [`run_region.sh`](../reference/shell.md#run_region.sh).
These include various data directory mounts for inputs, static forcing data files, intermediary outputs, and output realization files.

Regardless of build instruction, forcing configuration files are sourced from the container path `/ngen-app/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/`.

## Coastal Forcing

[`make_coastal_forcing.py`](../reference/python.md#make_coastal_forcingpy) runs the Forcing Engine in gridded mode to create atmospheric forcing inputs for coastal models. Example calls are provided by [`make_coastal_forcing.sh`](../reference/shell.md#make_coastal_forcing.sh). See the `nwm-coastal` repository for complete workflow and input-data setup documentation.

## Data Assimilation

[`run_output_postprocess.py`](../reference/python.md#run_output_postprocesspy) and [`run_output_mosaic.py`](../reference/python.md#run_output_mosaicpy) expose output-production and mosaicing workflows supplied by `nwm-data-assimilation`. See the `nwm-data-assimilation` repository for complete workflow and configuration documentation.
