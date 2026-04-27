# Build Architecture

## OS Image Inheritance

The ngen runtime environment (RTE) OS image is built from the following inheritance:

`ngen-forcing/Dockerfile.bmi-forcings`: Base image with packages `NextGen_Forcings_Engine_BMI` and `ewts`

&emsp; <span style="font-size: 18px;">&darr;</span>

`ngen/Dockerfile`: `ngen`, `partitionGenerator`, and various `extern` submodule packages

&emsp; <span style="font-size: 18px;">&darr;</span>

`nwm-rte/Dockerfile.rte`: RTE component packages

## RTE Component Packages

The RTE component Python packages include:

| Code Repository<br>(each includes 1 or more packages) | Python<br>Virtual Environment |
| ----------------------------------------------------- | -------------------------- |
| `nwm-fcst-mgr`                                          | `ngen-python` (default)     |
| `nwm-msw-mgr`                                           | `ngen-python` (default)     |
| `nwm-cal-mgr`                                           | `ngen-python` (default)     |
| `nwm-region-mgr`                                        | `ngen-python` (default)     |
| `nwm-data-assimilation`                                 | `ngen-python` (default)     |
| `nwm-verf`                                              | `eval_verf`                  |
| `nwm-eval-mgr`                                          | `eval_verf`                  |
