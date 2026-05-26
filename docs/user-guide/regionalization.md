# Regionalization Workflows

Regionalization workflows are ran via [`run_region.sh`](../reference/shell.md#run_region.sh) and associated Python script that is called: [`run_regionalization.py`](../reference/python.md#regionalization-workflows)

For Slurm execution, see: [`sbatch_run_region.sh`](../reference/shell.md#sbatch_run_region.sh)

For more information, see the documentation of the `nwm-region-mgr` repository.

## Caveats for Regionalization Workflows

At runtime, host disk mounts occur within [`run_region.sh`](../reference/shell.md#run_region.sh).
These include various data directory mounts for inputs, static forcing configuration files, intermediary outputs, and output realization files.

Regardless of build instruction, the host disk (local state) of the `ngen-forcing` files at the cloned repository path
`.../ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/` is used for forcing configuration files.
