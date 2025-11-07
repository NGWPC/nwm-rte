# NWM Runtime Environment

A configurable `docker build` and `docker run` sequence for headless end-to-end execution of ngen core + manager package capabilities.

## Description of Primary Files

[setup_workspace.sh](setup_workspace.sh) sources configuration from [config.bashrc](config.bashrc), downloads data from s3, and clones repos from GitHub.  Some data is mounted from those repos after cloning.  Other data is mounted from non-repo locations.

[ngen_rte_build.sh](ngen_rte_build.sh) sources configuration from [config.bashrc](config.bashrc), then builds an image using [Dockerfile.rte](Dockerfile.rte).

[ngen_rte_run.sh](ngen_rte_run.sh) uses `docker run` to start an ephemeral container of the new image with various host disk mounts applied, and runs a Python script in that container.  By default it runs [example_workflow.py](bin_mounted/example_workflow.py).

## Configuration Options

The ngen base image can be specified as a ghcr image, or as local source code (build from existing clone), or as remote source code (clone fresh or pull, then build).

The manager packages can be specified as local source code, or as remote source code (specifying a tag/branch/commit).  To switch the "sourcing mode" of the manager packages s.t. they install from local instead of from GitHub or vice-versa, currently it is required to comment/uncomment blocks of code in [Dockerfile.rte](Dockerfile.rte).

See notes in the files for additional details.


## Steps to Get Started

1. Clone this repo and enter it:

```shell
# Via ssh
git clone git@github.com:NGWPC/nwm-rte.git
# Enter the repo
cd nwm-rte
# Check out a branch (at time of writing, poc branch was appropriate)
git checkout poc
```

2. Review [config.bashrc](config.bashrc), edit variables as needed, in particular: `REPOS_COMMON_ROOT__HOST`, `NGEN_SOURCE_MODE`, `NGEN_BASE__REMOTE_GHCR_TAG`, and the branch choices for the various manager packages.

3. Download data, clone other repos, build the docker image, and run an example workflow:

```shell
# Set up s3 credentials before running.  This takes about 7 minutes.
time ./setup_data.sh |& tee setup_data.log
# Be ready to provide git credentials several times if prompted.  This takes about 3 minutes.
time ./setup_clone_repos.sh |& tee setup_clone_repos.log
# Be ready to supply sudo password if prompted.  This takes 2 to 5 minutes, depending which packages are installed, if using an existing GHCR image for ngen.
time ./ngen_rte_build.sh
# Be ready to supply sudo password if prompted
time ./ngen_rte_run.sh
```


## Additional Usage Notes

It should work to use s3fs if desired (host mounts s3, container mounts host), if not wanting to copy s3 data to the local disk.
