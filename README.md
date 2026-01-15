# NWM Runtime Environment

A configurable `docker build` and `docker run` sequence for headless end-to-end execution of ngen core + manager package capabilities.

## Description of Primary Files

[setup_data.sh](setup_data.sh) sources configuration from [config.bashrc](config.bashrc) and downloads data from s3.

[setup_clone_repos.sh](setup_clone_repos.sh) sources configuration from [config.bashrc](config.bashrc) and clones repos from GitHub.

[ngen_rte_build.sh](ngen_rte_build.sh) sources configuration from [config.bashrc](config.bashrc), then builds an image using [Dockerfile.rte](Dockerfile.rte).

[ngen_rte_run.sh](ngen_rte_run.sh) uses `docker run` to start an ephemeral container of the new image with various host disk mounts applied, and runs a Python script in that container.  By default it runs [run_tests.py](bin_mounted/run_tests.py).  Some data is mounted from cloned repos.  Other data is mounted from non-repo locations.

## Configuration Options

The ngen base image can be specified as a ghcr image, or as local source code (build from existing clone), or as remote source code (clone fresh or pull, then build).

The manager packages can be specified as local source code, or as remote source code (specifying a tag/branch/commit).  To switch the "sourcing mode" of the manager packages s.t. they install from local instead of from GitHub or vice-versa, currently it is required to comment/uncomment blocks of code in [Dockerfile.rte](Dockerfile.rte).

See notes in the files for additional details.


## Steps to Get Started

1. Make a directory to contain the repos and data, and enter it

This can be any location on your disk, but ~/ngwpc is a standard convention.
In a later step, a setup script will clone many repos into this location.
For each clone, if that particular repos already exists on your disk, it will skip that clone.
Meaning, it will not alter the state of the repos that you already have cloned, but it will clone additional repos as necessary.

```shell
mkdir -p ~/ngwpc && cd ~/ngwpc
```

1. Clone this repo and enter it:

```shell
git clone git@github.com:NGWPC/nwm-rte.git && cd nwm-rte
```

2. Check out a branch

```shell
git checkout development
```

3. Review [config.bashrc](config.bashrc), edit variables as needed, in particular: `REPOS_COMMON_ROOT__HOST`, `NGEN_SOURCE_MODE`, `NGEN_BASE__REMOTE_GHCR_TAG`, and the branch choices for various packages.

4. Clone other repos

```shell
# This clones repos. It will not alter the state of existing repos on your disk (for each clone, it skips if the folder already exists on disk).
# Be ready to provide git credentials several times if prompted.
time ./setup_clone_repos.sh
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
# If sourcing the ngen base image from an existing GHCR image, this is quick, and
# you may want to `docker pull` if pointing to a tag for the GHCR image (e.g. `latest`)
# rather than an explicit image hash.
time ./ngen_rte_build.sh
```

7. Run an example workflow

```shell
# This starts an ephemeral container of the ngen RTE image and runs a test workflow script (runs calibrations and forecasts).
# Be ready to supply sudo password if prompted.
# See CLI args in the example workflow script for details on behavior, and alternate test modes.
# Different ways of calling the example workflow script are provided as commented-out lines near the bottom of ngen_rte_run.sh
# After setting up RTE, the first run must be a calibration, to produce some files that are used by forecasts. After the first calibration run, subsequent forecasts can be ran without needing to re-run calibration.
time ./ngen_rte_run.sh
```


## Additional Usage Notes

It should work to use s3fs if desired (host mounts s3, container mounts host), if not wanting to copy s3 data to the local disk.
