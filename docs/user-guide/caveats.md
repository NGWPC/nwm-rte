# Caveats

## Files Sourced from Local NWM Repositories

See notes on [run configuration caveats](configuration.md#caveats). The local state of some NWM repositories is mounted at runtime, for static configuration files and and module parameters. In particular, see [regionalization caveats](auxilliary-workflows.md#caveats-for-regionalization-workflows)

## GHCR Images

If using a dynamic GHCR image tag such as `"latest"`, if you have already pulled that tag previously and you wish to update to the current version of that tag, you may need to run `docker pull`.

## Configuration Variables `REPO_TAG_NGEN_FORCING` and `REPO_TAG_EWTS`

The usage of the optional variable `REPO_TAG_NGEN_FORCING` in [`config.bashrc`](../reference/shell.md#config.bashrc) and in the GHA workflows, as well as the lowercase version `repo_tag_ngen_forcing` in the GHA workflows, has the effect of "reinstalling" specifically only the Python package of `ngen-forcing`. This is used for development purposes, for quickly trying changes to the Python package of `ngen-forcing`.

Using this optional variable does *not* cause a re-build of the entire `ngen-forcing` base. For example it does not incorporate changes to `ngen-forcing` C++ code or changes to `ngen-forcing/Dockerfile.bmi-forcings` or the various scripts or commands that are called by `ngen-forcing/Dockerfile.bmi-forcings`.

When `REPO_TAG_NGEN_FORCING` is set to an empty string, it has no effect, meaning, when it is an empty string then the extra `pip install` of `ngen-forcing` Python package does not occur on top of the existing ngen base image.

`REPO_TAG_EWTS` provides the equivalent optional Python-package reinstall for `nwm-ewts`. An empty string skips the reinstall. Like `REPO_TAG_NGEN_FORCING`, it does not rebuild the ngen base image.

The ngen base image contains `/ngen-app/ngen-bmi-forcing_git_info.json`, which records the `ngen-forcing` and `nwm-ewts` source versions included when that base image was built. The optional RTE reinstalls do not update or replace that inherited export. Instead, they write separate provenance files:

- `REPO_TAG_NGEN_FORCING` writes `/ngen-app/git-info/ngen-forcing_git_info.json`.
- `REPO_TAG_EWTS` writes `/ngen-app/git-info/nwm-ewts_git_info.json`.

The inherited export and the RTE reinstall records intentionally coexist so that the image retains provenance for both the original base-image contents and the later Python-package reinstall.
