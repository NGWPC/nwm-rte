"""
Command-line executable to build and run a "default" realization. Supports realtime forcing configurations, e.g. `"short_range"`, as well as historical/retrospective sources, e.g. `"aorc"`.

This runs inside the ngen runtime environment.
The CLI structure is mimicked in part by `configs.RTEDefaultConfig`.
For settings that are not exposed by CLI arguments, see primarily `consts.py`.

See `run_default.sh` for example calls.
"""

import argparse

from mswm.build_inputs import RealizationBuilder

from ngen_rte.configs import RTEDefaultConfig
from ngen_rte.execution.ngen_async import NgenRunnerAsync
from ngen_rte.logger import initialize_logger
from ngen_rte.run_config import cli_args
from ngen_rte.tests import utils_testing_setup
from ngen_rte.utils import (
    _rte_transmit_job_complete,
    _rte_transmit_job_failed,
    _rte_transmit_job_start,
    build_realization,
    transmit,
)

LOG = initialize_logger()


def run_default(rb: RealizationBuilder) -> NgenRunnerAsync:
    """Run the provided default realization.
    Realization should already be built (rb.build_default_realization() already called).
    """
    LOG.info("Running default realization")
    # For default realization, currently postprocess needs suppress_output=True
    ngen_runner = NgenRunnerAsync(rb=rb, postprocess=True, suppress_output=True)
    ngen_runner.start()
    ngen_runner.stream_status_until_complete()
    ngen_runner.close()  # Can also let __del__ handle this.
    return ngen_runner


def _main(cfg: RTEDefaultConfig):
    # util_asserts.assert_paths__core(forecast_vars.gage_id)
    # util_asserts.assert_paths_common_input()

    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()

    use_cold_start = bool(cfg.cold_start_datetime)

    rb = build_realization(
        cfg.mswm_RealizationBuilder_kwargs | {"use_cold_start": use_cold_start},
        build_method="build_default_realization"
    )
    cfg.configure_ngen_log(rb)
    run_default(rb)


def main(cfg: RTEDefaultConfig):
    _rte_transmit_job_start()
    try:
        _main(cfg)
    except Exception as e:
        transmit(exc=e)
        _rte_transmit_job_failed()
        raise e
    else:
        _rte_transmit_job_complete()


def cli_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="""Script for building and running default realizations
using realtime forcing configurations or historical / retrospective forcing.
The CLI arguments mostly follow that of run_forecast.py. The exception is
that "--duration" aka "-dur" (in days) was added to this script
to support the historical / retrospective forcing use case, e.g. AORC or NWM.""",
        formatter_class=cli_args.HelpFormatter,
    )
    cli_args.add_args_for_script(parser, cli_args.Script.DEFAULT)
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    main(cfg=RTEDefaultConfig(**vars(args)))
