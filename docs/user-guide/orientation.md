# Orientation


## Description of Primary Files

Most of the shell files source their configuration from [`config.bashrc`](../reference/shell.md#config.bashrc).

[`setup_data.sh`](../reference/shell.md#setup_data.sh) Downloads global data from s3, as well as data for specific test gage(s).

[`setup_data_one_gage.sh`](../reference/shell.md#setup_data_one_gage.sh): Downloads data from s3 for a specific test gage. This is used to optionally download data for non-default gages, and for oCONUS gages.

[`setup_clone_repos.sh`](../reference/shell.md#setup_clone_repos.sh) Clones repos from GitHub. Includes CLI option for using SSH (for r+w, requires credentials) or HTTPS (for read-only, no credentials required). Includes CLI option for a shallow (`--depth 1`) clone or full clone.

[`ngen_rte_build.sh`](../reference/shell.md#ngen_rte_build.sh) Builds an image using `Dockerfile.rte`.

[`run.sh`](../reference/shell.md#run.sh) Defines a bash function `docker_run` that uses a `docker run` call to start an ephemeral container of the new image with various host disk mounts applied. This is intended to be sourced by other shell scripts. The `docker_run` function receives any number of positional arguments. It passes its first argument as the value for Docker's `--entrypoint` and passes all subsequent arguments to the container as a command. See [`run_calib.sh`](../reference/shell.md#run_calib.sh) for an example. If [`run.sh`](../reference/shell.md#run.sh) is executed as a script e.g. `./run.sh`, then it starts an interactive terminal session in the container.


## `ngen` Logs

The log levels of `ngen` and its various modules is set via [`bin_mounted/ngen_logging.json`](../ngen_logging.json). When RTE builds a realization, it copies this file into a location where `ngen` finds it during its run.

The OS environment variable `NGEN_RESULTS_DIR` dictates where this json file should be when `ngen` starts, and also controls where the output log files are written.

### `NGEN_LOG_TO_RTE`

RTE exposes an optional variable `NGEN_LOG_TO_RTE` in [`config.bashrc`](../reference/shell.md#config.bashrc).

When this is `"YES"` or `"TRUE"` then RTE will set `NGEN_RESULTS_DIR` before it calls the calibration manager module or the forecast manager module. It will set it to a location within the RTE repository directory: `ngen_logs/{YYYYMMDD_HHMMSS_FFFFFF}_{description}/` where the time is the current UTC time to microseconds, and the description varies.

When this is `"NO"`, `"FALSE"`, or unset, then RTE will set `NGEN_RESULTS_DIR` to a path within the realization's directory, after building the realization. This mimics the behavior of the calibration manager module and the forecast manager module when those are ran from the alternate ngenCERF environment (those modules set `NGEN_RESULTS_DIR` automatically if it is not set).

In either case, RTE copies [`bin_mounted/ngen_logging.json`](../ngen_logging.json) into `NGEN_RESULTS_DIR`, after it defines `NGEN_RESULTS_DIR` and before starting ngen.

### Realization Executables

For the following executables, see commented-out lines in the script for examples of different ways to leverage the [CLI arguments of the executable Python modules](../reference/python.md#cli-help-menus).

[`run_default.sh`](../reference/shell.md#run_default.sh) Builds and runs a "default" realization via call to [`bin_mounted/run_default.py`](../reference/python.md#run_defaultpy) and a checkpoint restart via call to [`bin_mounted/run_restart.py`](../reference/python.md#run_restartpy).

[`run_calib.sh`](../reference/shell.md#run_calib.sh) Builds and runs a "calibration" realization via call to [`bin_mounted/run_calibration.py`](../reference/python.md#run_calibrationpy).

[`run_fcst.sh`](../reference/shell.md#run_fcst.sh) Builds and runs a "forecast" realization via call [`bin_mounted/run_forecast.py`](../reference/python.md#run_forecastpy).

[`run_suite.sh`](../reference/shell.md#run_suite.sh) Builds and runs a series of calibration and forecast realizations in a series of calls to [`bin_mounted/run_calibration.py`](../reference/python.md#run_calibrationpy) and [`bin_mounted/run_forecast.py`](../reference/python.md#run_forecastpy).

[`run_tests.sh`](../reference/shell.md#run_tests.sh) Builds and runs a series of calibration and forecast realizations in one call to [`bin_mounted/run_tests.py`](../reference/python.md#run_testspy). If one of the realizations experiences an error, the process will continue to the next realization without halting. This workflow extracts information from the log files of the various realizations, and writes a json structure to disk with certain log lines and status of each realization's build step and run step. By default this workflow allows the realizations run to completion, but also supports modes that cancel the realization after a certain amount of time.


## See Also

[Python CLI Interface](../reference/python.md#cli-help-menus)

[Dev Container and Debugger](devcon-debug.md)

[Configuration](configuration.md)

[Code Reference](../reference/home.md)
