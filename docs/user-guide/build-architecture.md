# Build Architecture

## OS Image Inheritance

The ngen runtime environment (RTE) OS image is built via image inheritance:

`ngen-forcing/Dockerfile.bmi-forcings`: Base image with `ngen-forcing` code and `ewts` package

&emsp; &emsp; <span style="font-size: 24px;">&darr;</span>

`ngen/Dockerfile`: `ngen` and packages from its `extern` submodules

&emsp; &emsp; <span style="font-size: 24px;">&darr;</span>

`nwm-rte/Dockerfile.rte`: RTE layers

## RTE Layers

The RTE layers include the following component packages:

| Code Repository<br>(each includes 1 or more packages) | Python Virtual Environment |
| ----------------------------------------------------- | -------------------------- |
| nwm-fcst-mgr                                          | ngen-python (default)     |
| nwm-msw-mgr                                           | ngen-python (default)     |
| nwm-cal-mgr                                           | ngen-python (default)     |
| nwm-region-mgr                                        | ngen-python (default)     |
| nwm-data-assimilation                                 | ngen-python (default)     |
| nwm-verf                                              | eval_verf                  |
| nwm-eval-mgr                                          | eval_verf                  |
