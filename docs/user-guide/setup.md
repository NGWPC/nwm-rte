# Setup (Get Started)

## Steps to Set Up

#### Make a directory to contain the repos and data, and enter it

This can be any location on your disk, but ~/ngwpc is a standard convention.
In a later step, a setup script will clone many repos into this location.
For each clone, if that particular repos already exists on your disk, it will not affect the contents of that existing directory.

```shell
mkdir -p ~/ngwpc && cd ~/ngwpc
```

#### Clone this repo and enter it, using either SSH or HTTPS:

```shell
### Via SSH (use your GitHub auth, for read-write access)
git clone git@github.com:NGWPC/nwm-rte.git && cd nwm-rte
### Or via HTTPS (no auth required, for read-only access)
git clone https://github.com/NGWPC/nwm-rte.git && cd nwm-rte
```

#### Check out a branch

```shell
git checkout development
```

#### Review `config.bashrc` and edit variables as needed for your desired build configuration. Note that many of the variables' values are set to use existing environment variables if they are already defined, rather than the value set in the `config.bashrc` file.

#### Clone other repos

```shell
# This clones repos. It will not alter the state of existing repos on your disk (for each clone, it skips if the folder already exists on disk).
# This script has two positional arguments, for specifying whether you wish to clone via SSH or via HTTPS, and whether to perform a shallow clone. The second argument is optional, and defaults to 'full' if not provided.
### Via SSH (use your GitHub auth, for read-write access)
### Be ready to provide git credentials several times if prompted.
time ./setup_clone_repos.sh ssh
### Or via HTTPS (no auth required, for read-only access)
time ./setup_clone_repos.sh https
```

#### Download data.

**Note:** Run once, either with or without `-r` flag for regionalization data.

```shell
# You need to set up s3 credentials before running.
time ./setup_data.sh
```

```shell
# OPTIONAL: Pass the -r argument to download regionalization data.
time ./setup_data.sh -r
```


## Steps to Build

#### Build the Docker image

```shell
# This builds a local Docker image of ngen RTE, containing ngen base + component packages.
# Be ready to supply sudo password if prompted.
# If leveraging any remote Docker images (e.g. GHCR), you may want to run one or more `docker pull` commands before building.
# For example: docker pull ghcr.io/ngwpc/ngen:latest
time ./ngen_rte_build.sh
```

## Steps to Run

#### Run an example workflow

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

## See Also

[Dev Container and Debugger](devcon-debug.md)

[Configuration](configuration.md)

[Code Reference](../reference/home.md)

[Regionalization Workflows](regionalization.md)
