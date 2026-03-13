# NWM Runtime Environment

A configurable `docker build` and `docker run` sequence for headless end-to-end execution of ngen core + manager package capabilities.

## Caveats

### Optional REPO_TAG_NGEN_FORCING

The usage of the optional variable `REPO_TAG_NGEN_FORCING` in `config.bashrc` and in the GHA workflows, as well as the lowercase version `repo_tag_ngen_forcing` in the GHA workflows, has the effect of "reinstalling" specifically only the Python package of ngen-forcing. This is used for development purposes, for quickly trying changes to the Python package of ngen-forcing.

Using this optional variable does *not* cause a re-build of the entire ngen-forcing base. For example it does not incorporate changes to ngen-forcing C++ code or changes to `ngen-forcing/Dockerfile.bmi-forcings` or the various scripts or commands that are called by `ngen-forcing/Dockerfile.bmi-forcings`.

When `REPO_TAG_NGEN_FORCING` is set to an empty string, it has no effect, meaning, when it is an empty string then the extra `pip install` of ngen-forcing Python package does not occur on top of the existing ngen base image.

## Description of Primary Files

Most of the shell files source their configuration from [config.bashrc](config.bashrc).

[setup_data.sh](setup_data.sh) Downloads global data from s3, as well as data for specific test gage(s).

[setup_data_one_gage.sh](setup_data_one_gage.sh): Downloads data from s3 for a specific test gage. This is used to optionally download data for non-default gages, and for oCONUS gages.

[setup_clone_repos.sh](setup_clone_repos.sh) Clones repos from GitHub. Includes CLI option for using SSH (for r+w, requires credentials) or HTTPS (for read-only, no credentials required). Includes CLI option for a shallow (`--depth 1`) clone or full clone.

[ngen_rte_build.sh](ngen_rte_build.sh) Builds an image using [Dockerfile.rte](Dockerfile.rte).

[run.sh](run.sh) Defines a bash function `docker_run` that uses a `docker run` call to start an ephemeral container of the new image with various host disk mounts applied. This is intended to be sourced by other shell scripts. The `docker_run` function receives any number of positional arguments. It passes its first argument as the value for Docker's `--entrypoint` and passes all subsequent arguments to the container as a command. See [run_calib.sh](run_calib.sh) for an example. If [run.sh](run.sh) is executed as a script e.g. `./run.sh`, then it starts an interactive terminal session in the container.

## `ngen` Logs

The log levels of `ngen` and its various modules is set via `./bin_mounted/ngen_logging.json`. When RTE builds a realization, it copies this file into a location where `ngen` finds it during its run.

The OS environment variable `NGEN_RESULTS_DIR` dictates where this json file should be when `ngen` starts, and also controls where the output log files are written.

### `NGEN_LOG_TO_RTE`

RTE exposes an optional variable `NGEN_LOG_TO_RTE` in `config.bashrc`.

When this is set to `true` then RTE will set `NGEN_RESULTS_DIR` before it calls the calibration manager module or the forecast manager module. It will set it to a location within the RTE repository directory: `ngen_logs/{YYYYMMDD_HHMMSS_FFFFFF}_{description}/` where the time is the current UTC time to microseconds, and the description is defined ad hoc.

When `NGEN_LOG_TO_RTE` is `false` or unset, this will cause RTE to set `NGEN_RESULTS_DIR` to a path within the realization's directory, after building the realization. This mimics the behavior of the calibration manager module and the forecast manager module when those are ran from the alternate ngenCERF environment (those modules set `NGEN_RESULTS_DIR` automatically if it is not set).

For RTE, in all cases, RTE copies `./bin_mounted/ngen_logging.json` into `NGEN_RESULTS_DIR`, after it defines `NGEN_RESULTS_DIR` and before starting ngen.


### Realization Executables

For the following executables, see commented-out lines in the script for examples of different ways to leverage the CLI args exposed by the various workflows.

[run_calib.sh](run_calib.sh) Builds and runs one calibration realization in one call to [bin_mounted/run_calibration.py](bin_mounted/run_calibration.py).

[run_fcst.sh](run_fcst.sh) Builds and runs one forecast realization in one call to [bin_mounted/run_forecast.py](bin_mounted/run_forecast.py).

[run_suite.sh](run_suite.sh) Builds and runs a series of calibration and forecast realizations in a series of calls to [bin_mounted/run_calibration.py](bin_mounted/run_calibration.py) and [bin_mounted/run_forecast.py](bin_mounted/run_forecast.py).

[run_tests.sh](run_tests.sh) Builds and runs a series of calibration and forecast realizations in one call to [bin_mounted/run_tests.py](bin_mounted/run_tests.py). If one of the realizations experiences an error, the process will continue to the next realization without halting. This workflow extracts information from the log files of the various realizations, and writes a json structure to disk with certain log lines and status of each realization's build step and run step. By default this workflow allows the realizations run to completion, but also supports modes that cancel the realization after a certain amount of time.

## Configuration Options

See notes within [config.bashrc](config.bashrc) for additional details.

The ngen base image (which in turn has `ngen-forcing` as its base) can be an existing ghcr image, an existing local Docker image, or be built from source using remote code or existing code already on disk.

The manager packages can be installed from remote code or existing code already on disk.

The tags and branch names of source code repositories and/or existing GHCR images are configurable.

Many of the variables in [config.bashrc](config.bashrc) are set to use existing values if pre-defined, effectively allowing for OS environment variables to override what is in the file.


## Steps to Get Started

1. Make a directory to contain the repos and data, and enter it

This can be any location on your disk, but ~/ngwpc is a standard convention.
In a later step, a setup script will clone many repos into this location.
For each clone, if that particular repos already exists on your disk, it will not affect the contents of that existing directory.

```shell
mkdir -p ~/ngwpc && cd ~/ngwpc
```

1. Clone this repo and enter it, using either SSH or HTTPS:

```shell
### Via SSH (use your GitHub auth, for read-write access)
git clone git@github.com:NGWPC/nwm-rte.git && cd nwm-rte
### Or via HTTPS (no auth required, for read-only access)
git clone https://github.com/NGWPC/nwm-rte.git && cd nwm-rte
```

2. Check out a branch

```shell
git checkout development
```

3. Review [config.bashrc](config.bashrc) and edit variables as needed for your desired build configuration. Note that many of the variables' values are set to use existing environment variables if they are already defined, rather than the value set in the [config.bashrc](config.bashrc) file.

4. Clone other repos

```shell
# This clones repos. It will not alter the state of existing repos on your disk (for each clone, it skips if the folder already exists on disk).
# This script has two positional arguments, for specifying whether you wish to clone via SSH or via HTTPS, and whether to perform a shallow clone. The second argument is optional, and defaults to 'full' if not provided.
### Via SSH (use your GitHub auth, for read-write access)
### Be ready to provide git credentials several times if prompted.
time ./setup_clone_repos.sh ssh
### Or via HTTPS (no auth required, for read-only access)
time ./setup_clone_repos.sh https
```

5. Download data.

**Note:** Run once, either with or without `-r` flag for regionalization data.

```shell
# You need to set up s3 credentials before running.
time ./setup_data.sh
```

```shell
# OPTIONAL: Pass the -r argument to download regionalization data.
time ./setup_data.sh -r
```

6. Build the Docker image

```shell
# This builds a local Docker image of ngen RTE, containing ngen base + component packages.
# Be ready to supply sudo password if prompted.
# If leveraging any remote Docker images (e.g. GHCR), you may want to run one or more `docker pull` commands before building.
# For example: docker pull ghcr.io/ngwpc/ngen:latest
time ./ngen_rte_build.sh
```

7. Run an example workflow

```shell
# These start an ephemeral container of the ngen RTE image
# and run one or more reailzations.
# Be ready to supply sudo password if prompted.
# See CLI args in the Python scripts within `bin_mounted/`
# and additional example calls in the shell scripts listed here.
### Atomic execution: build and run one calibration realization, then build and run one forecast realization.
time ./run_calib.sh
time ./run_fcst.sh
### Build and run several calibration and forecast realizations in series.
time ./run_suite.sh
### Run many realizations in series and report results, continuing through the list if one experiences an error.
time ./run_tests.sh
```

## Regionalization Workflows

Regionalization workflows are ran via [run_region.sh](run_region.sh) and associated Python script(s) that are called. See the header section of the script for usage help. For more information, see the documentation of the `nwm-region-mgr` repository.

## Example for a Custom Build of `ngen`

Here are steps for making the RTE image using a custom version of `ngen`. These steps assume that the default version of `ngen-forcing` (referenced by `ngen/Dockerfile`) is the desired base, prior to adding the `ngen` layer.

1. Run the above setup steps for cloning repos and downloading data, except stop before running `./ngen_rte_build.sh`.
2. Edit `config.bashrc` to use: `NGEN_SOURCE_MODE="build_from_local"`
3. Check out the desired code for ngen and its submodules.  For example, to use `ngen`'s `development` branch but change the version of `t-route`:

```
### From the ~/ngwpc/ngen repository root:
git checkout development
git pull
## Ensure the local copies of submodules are matching the specific commits currently pointed to by the ngen repository.
## This does not fetch the latest updates from the submodule branches tracked by .gitmodules.  To do that, you would add --remote to the command.
git submodule update --init --recursive
## Check out a specific branch of t-route
( cd extern/t-route && git checkout any-branch && git pull )
```

4. If your `ngen/Dockerfile` is starting `FROM ghcr.io/ngwpc/ngen-bmi-forcing:latest`, then pull the latest ngen-forcing GHCR image.

`sudo docker pull ghcr.io/ngwpc/ngen-bmi-forcing:latest`

5. Build the RTE image

```
### From the ~/ngwpc/nwm-rte repository root:
./ngen_rte_build.sh
```

6. Confirm in the build messages that the built was successful and that the image name built is `ngen_rte:build_from_local`
