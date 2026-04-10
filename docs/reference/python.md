# Python Code Reference

The `pyproject.toml` of this repository is minimal because the runtime environment's Python packages are included in base images (`ngen-forcing -> ngen`) as well as the layers that nwm-rte adds during its build sequence, which inherits from `ngen`.

The `pyproject.toml` of this repository primarily contains requirements needed to build this documentation.

# CLI Executables

These are command-line executable scripts. They must run inside the RTE

::: run_default

::: run_calibration

::: run_forecast

::: run_regionalization

# Configuration Classes

These mimic the CLI interfaces and perform some additional argument parsing and preparation of classes that are passed to other components of the system.

::: configs

<!-- ::: configs.RTESetup
    options:
      show_source: true
      members: true

::: configs.RTEDefaultConfig
    options:
      show_source: true
      members: true -->
