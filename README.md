# run-time-environment-trial
A configurable Docker build for ngen + manager (component) packages

[ngen_rte_build.sh](ngen_rte_build.sh) sources configuration from [config.bashrc](config.bashrc), then builds an image using [Dockerfile.rte](Dockerfile.rte), then uses `docker run` to start an ephemeral container of the new image with various host disk mounts applied, and run a Python script in that container.

The ngen base image can be specified as a ghcr image, or as local source code, or as remote source code.

The manager packages can be specified as local source code, or as remote source code (specifying a tag/branch/commit).  To switch the "sourcing mode" of the manager packages s.t. they install from local instead of from GitHub or vice-versa, currently it is required to comment/uncomment blocks of code in [Dockerfile.rte](Dockerfile.rte).

See notes in [ngen_rte_build.sh](ngen_rte_build.sh) and [config.bashrc](config.bashrc) for more details.
