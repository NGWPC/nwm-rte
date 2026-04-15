# Configuration

## Build Configuration

The build configuration settings are made in `config.bashrc`. 

Variables in that file allow choosing the sources of the base `ngen-forcing` image, the base `ngen` image, as well as all RTE component packages.

The base images may be sourced from remote GHCR images, built from local code, or built from remote GH code.

The component packages may be installed from local code or installed from remote GH code.

Sourcing from remote allows the user to specify any GitHub "reference" name, i.e. a specific branch, tag, or commit hash.

### See Also

[reference/shell.md#config.bashrc](../reference/shell.md#config.bashrc)


## Run Configuration

Most run settings are made via command-line interface arguments of the various executable Python modules within `bin_mounted/`.

Some run settings are configured in `bin_mounted/consts.py`, `bin_mounted/ngen_logging.json`, and `config.bashrc`.

Runtime host disk mounts occur within `run.sh`.  These include various data directory mounts for inputs, intermediary outputs, and realization files, as well as configuration files mounted from locally cloned host disk files for `ngen-forcing`.

### See Also

[Python CLI Help](../reference/python.md#cli-help-menus)

[config.bashrc](../reference/shell.md#config.bashrc)

[run.sh](../reference/shell.md#run.sh)

[bin_mounted/ngen_logging.json](../ngen_logging.json)

[bin_mounted/consts.py](../reference/python.md#consts)


## Dev Container and Debugger Configuration

[Dev Container and Debugger](devcon-debug.md)
