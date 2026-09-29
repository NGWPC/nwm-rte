# Build Architecture

## OS Image Inheritance

The ngen runtime environment (RTE) OS image is built from the following inheritance:

`ngen-forcing/Dockerfile.bmi-forcings`: Base image with packages `NextGen_Forcings_Engine_BMI` and `ewts`

&emsp; <span style="font-size: 18px;">&darr;</span>

`ngen/Dockerfile`: `ngen`, `partitionGenerator`, and various `extern` submodule packages

&emsp; <span style="font-size: 18px;">&darr;</span>

`nwm-rte/Dockerfile.rte`: RTE component packages

See the [Build Flow diagram](../diagrams/build.md).

## Tested Platforms and Python Versions

The build has been tested with Rocky Linux 8 and Debian 12 (Bookworm), and with ngen base images using Python 3.11 and Python 3.12. The current default image lineage uses Debian 12 and Python 3.12.

`nwm_eval` is installed in a separate Python 3.11 virtual environment because its pinned dependencies are not compatible with Python 3.12.

`Dockerfile.rte` has also been tested with Podman in an unmerged branch. The resulting image built and ran the RTE pytest realization successfully. Podman is not exercised by the repository's CI workflow.

## RTE Component Packages

The RTE component Python packages include:

| Code Repository<br>(each includes 1 or more packages) | Python<br>Virtual Environment |
| ----------------------------------------------------- | -------------------------- |
| `nwm-fcst-mgr`                                          | `ngen-python` (default)     |
| `nwm-msw-mgr`                                           | `ngen-python` (default)     |
| `nwm-cal-mgr`                                           | `ngen-python` (default)     |
| `nwm-region-mgr`                                        | `ngen-python` (default)     |
| `nwm-data-assimilation`                                 | `ngen-python` (default)     |
| `nwm-eval-mgr`                                          | `eval_verf`                  |

The `nwm-cal-mgr` package must be installed even when calibration workflows are not used because RTE modules import `calib.strategy` during normal startup.

## External Access and Runtime

Typical builds access GitHub and GHCR. Data setup also requires S3 and the EDFS streamflow-observations API. Building a realization requires the EDFS hydrofabric API unless existing local hydrofabric data is provided.

## Image Provenance

The image records OCI provenance labels and source metadata JSON files. Base-image records are inherited under `/ngen-app/`; RTE-installed package records are written under `/ngen-app/git-info/`. See [Caveats](caveats.md#configuration-variables-repo_tag_ngen_forcing-and-repo_tag_ewts) for behavior of alternative build options that involve "reinstalling" Python packages from `nwm-ewts` and `ngen-forcing` (for developing and testing).
