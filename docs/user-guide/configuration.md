# Configuration

## Build Configuration

The build configuration settings are made in [`config.bashrc`](../reference/shell.md#config.bashrc). 

Variables in that file allow choosing the sources of the base `ngen-forcing` image, the base `ngen` image, as well as all RTE component packages.

The base images may be sourced from remote GHCR images, built from local code, or built from remote GH code.

The component packages may be installed from local code or installed from remote GH code.

Sourcing from remote allows the user to specify any Git "reference" or "ref" name, i.e. a specific branch, tag, or commit hash from GitHub.


## Run Configuration

Most run settings are made via [CLI arguments of the executable Python modules](../reference/python.md#cli-help-menus) within `bin_mounted/`.

Some run settings are configured in [`bin_mounted/ngen_rte/consts.py`](../reference/python.md#python-constants), [`bin_mounted/ngen_rte/run_config/ngen_logging.json`](../ngen_logging.json), [`config.bashrc`](../reference/shell.md#config.bashrc), and in some conditions [`bin_mounted/ngen_rte/run_config/ngen_forcing_vers.json`](../ngen_forcing_vers.json)

## Caveats

### GHCR Images

If using a dynamic GHCR image tag such as `"latest"`, if you have already pulled that tag previously and you wish to update to the current version of that tag, you may need to run `docker pull`

### Local Files for Runtime Mounts

At runtime, host disk mounts occur within [`run.sh`](../reference/shell.md#run.sh).  These include various data directory mounts for input data, intermediary output data, and output realizations.

## Dev Container and Debugger Configuration

[Dev Container and Debugger](devcon-debug.md)
