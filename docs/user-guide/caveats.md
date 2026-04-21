# Caveats

## Files Sourced from Local NWM Repositories

See notes on [run configuration caveats](configuration.md#caveats). The local state of some NWM repositories is mounted at runtime, for static configuration files and and module parameters.

## GHCR Images

If using a dynamic GHCR image tag such as `"latest"`, if you have already pulled that tag previously and you wish to update to the current version of that tag, you may need to run `docker pull`.

## Configuration Variable `REPO_TAG_NGEN_FORCING`

The usage of the optional variable `REPO_TAG_NGEN_FORCING` in [`config.bashrc`](../reference/shell.md#config.bashrc) and in the GHA workflows, as well as the lowercase version `repo_tag_ngen_forcing` in the GHA workflows, has the effect of "reinstalling" specifically only the Python package of `ngen-forcing`. This is used for development purposes, for quickly trying changes to the Python package of `ngen-forcing`.

Using this optional variable does *not* cause a re-build of the entire `ngen-forcing` base. For example it does not incorporate changes to `ngen-forcing` C++ code or changes to `ngen-forcing/Dockerfile.bmi-forcings` or the various scripts or commands that are called by `ngen-forcing/Dockerfile.bmi-forcings`.

When `REPO_TAG_NGEN_FORCING` is set to an empty string, it has no effect, meaning, when it is an empty string then the extra `pip install` of `ngen-forcing` Python package does not occur on top of the existing ngen base image.
