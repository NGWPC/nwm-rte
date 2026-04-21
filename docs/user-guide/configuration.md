# Configuration

## Build Configuration

The build configuration settings are made in [`config.bashrc`](../reference/shell.md#config.bashrc). 

Variables in that file allow choosing the sources of the base `ngen-forcing` image, the base `ngen` image, as well as all RTE component packages.

The base images may be sourced from remote GHCR images, built from local code, or built from remote GH code.

The component packages may be installed from local code or installed from remote GH code.

Sourcing from remote allows the user to specify any Git "reference" or "ref" name, i.e. a specific branch, tag, or commit hash from GitHub.


## Run Configuration

Most run settings are made via [CLI arguments of the executable Python modules](../reference/python.md#cli-help-menus) within `bin_mounted/`.

Some run settings are configured in [`bin_mounted/consts.py`](../reference/python.md#python-constants), [`bin_mounted/ngen_logging.json`](../ngen_logging.json), and [`config.bashrc`](../reference/shell.md#config.bashrc).

## Caveats

### GHCR Images

If using a dynamic GHCR image tag such as `"latest"`, if you have already pulled that tag previously and you wish to update to the current version of that tag, you may need to run `docker pull`

### Local Files for Runtime Mounts

At runtime, host disk mounts occur within [`run.sh`](../reference/shell.md#run.sh).  These include various data directory mounts for inputs, static forcing configuration files, module parameters, intermediary outputs, and output realization files.

Regardless of build instruction, the local state of files from the following repositories is used:

`ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/`

`nwm-msw-mgr/src/mswm/module_parameter_files/`


## Dev Container and Debugger Configuration

[Dev Container and Debugger](devcon-debug.md)
