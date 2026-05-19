"""
Command-line executable to build and run a "default" realization. Supports realtime forcing configurations, e.g. `"short_range"`, as well as historical/retrospective sources, e.g. `"aorc"`.

This runs inside the ngen runtime environment.
The CLI structure is mimicked in part by `configs.RTEDefaultConfig`.
For settings that are not exposed by CLI arguments, see primarily `consts.py`.

See `run_default.sh` for example calls.
"""

import argparse
import functools

from mswm.build_inputs import RealizationBuilder

from ngen_rte.configs import RTEDefaultConfig
from ngen_rte.execution.ngen_async import NgenRunnerAsync
from ngen_rte.run_config import cli_args
from ngen_rte.tests import utils_testing_setup
from ngen_rte.utils import configure_ngen_log

print = functools.partial(print, flush=True)


def build_default_realization(cfg: RTEDefaultConfig) -> RealizationBuilder:
    """Build and return a non-coldstart forecast realization"""
    print("Building default realization...")
    rb = RealizationBuilder(**cfg.mswm_RealizationBuilder_kwargs)
    rb.build_default_realization()
    configure_ngen_log(rb.work_dir, "default")
    return rb


def run_default(rb: RealizationBuilder, cfg: RTEDefaultConfig) -> None:
    """Run the provided default realization.
    Realization should already be built (rb.build_default_realization() already called).
    """
    print(
        f"Running default realization with configuration: {cfg.mswm_RealizationBuilder_kwargs}"
    )
    ngen_runner = NgenRunnerAsync(cfg=cfg, rb=rb)
    ngen_runner.start()
    ngen_runner.stream_status_until_complete()


def main(cfg: RTEDefaultConfig):
    # util_asserts.assert_paths__core(forecast_vars.gage_id)
    # util_asserts.assert_paths__raw_config()
    # util_asserts.assert_paths_common_input()

    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()

    rb = build_default_realization(cfg)
    run_default(rb, cfg)


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
