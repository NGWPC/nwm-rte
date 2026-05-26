"""
Command-line executable to build and run a "forecast" realization, optionally with a coldstart.

This runs inside the ngen runtime environment.
The CLI structure is mimicked in part by `configs.RTEForecastConfig`.
For settings that are not exposed by CLI arguments, see primarily `consts.py`.

See `run_fcst.sh` for example calls.
"""

import argparse
import functools

from mswm.build_inputs import RealizationBuilder

from ngen_rte.configs import RTEForecastConfig
from ngen_rte.execution.ngen_async import NgenRunnerAsync
from ngen_rte.run_config import cli_args
from ngen_rte.tests import utils_testing_setup
from ngen_rte.utils import build_realization

print = functools.partial(print, flush=True)


def run_realization(rb: RealizationBuilder, cfg: RTEForecastConfig) -> None:
    """Run the realization, which can be a coldstart, forecast, or lagged ensemble."""
    # partition_file = getattr(rb, "part_file", None)

    print(
        f"Running realization with Forcing configuration: {rb.input_configs['Forcing']}"
    )

    if rb.use_hindcast:
        raise NotImplementedError("use_hindcast not yet implemented in nwm-rte")
    elif rb.use_warm_start:
        raise NotImplementedError("use_warm_start not yet implemented in nwm-rte")
    else:
        ngen_runner = NgenRunnerAsync(
            cfg=cfg, rb=rb, postprocess=True, suppress_output=False
        )
        ngen_runner.start()
        ngen_runner.stream_status_until_complete()
        ngen_runner.close()  # Can also let __del__ handle this.


def main(cfg: RTEForecastConfig):
    # util_asserts.assert_paths__core(forecast_vars.gage_id)
    # util_asserts.assert_paths__raw_config()
    # util_asserts.assert_paths_common_input()

    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()

    if cfg.cold_start_datetime:
        rb_cs = build_realization(
            cfg.mswm_RealizationBuilder_kwargs | {"use_cold_start": True},
            "build_fcst_realization",
        )
        cfg.configure_ngen_log(rb_cs)
        run_realization(rb_cs, cfg)

    if cfg.cycle_datetime:
        rb_fcst = build_realization(
            cfg.mswm_RealizationBuilder_kwargs | {"use_cold_start": False},
            "build_fcst_realization",
        )
        cfg.configure_ngen_log(rb_fcst)
        run_realization(rb_fcst, cfg)


def cli_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="""Script for building and running a forecast realization,
optionally with a coldstart.""",
        formatter_class=cli_args.HelpFormatter,
    )
    cli_args.add_args_for_script(parser, cli_args.Script.FORECAST)
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    main(cfg=RTEForecastConfig(**vars(args)))
