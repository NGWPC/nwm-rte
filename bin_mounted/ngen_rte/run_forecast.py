"""
Command-line executable to build and run a "forecast" realization, optionally with a coldstart.

This runs inside the ngen runtime environment.
The CLI structure is mimicked in part by `configs.RTEForecastConfig`.
For settings that are not exposed by CLI arguments, see primarily `consts.py`.

See `run_fcst.sh` for example calls.
"""

import argparse

from mswm.build_inputs import RealizationBuilder
from nwm_fcst_mgr.forecast import run_hindcast

from ngen_rte.configs import RTEForecastConfig
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


def run_realization(rb: RealizationBuilder) -> None:
    """Run the realization, which can be a coldstart, forecast, or lagged ensemble."""
    LOG.info(
        f"Running realization with Forcing configuration: {rb.input_configs['Forcing']}"
    )
    if rb.run_type in ("hindcast", "warm_start"):
        do_override_log_file_prefix = True
    else:
        do_override_log_file_prefix = False
    if False:
        raise NotImplementedError(
            "This is a placeholder exception for unallowed execution paths"
        )
    else:
        ngen_runner = NgenRunnerAsync(
            rb=rb,
            postprocess=True,
            suppress_output=False,
            # timeout_secs=10,
            do_override_log_file_prefix=do_override_log_file_prefix,
        )
        ngen_runner.start()
        ngen_runner.stream_status_until_complete()
        ngen_runner.close()  # Can also let __del__ handle this.


def _main(cfg: RTEForecastConfig):
    # util_asserts.assert_paths__core(forecast_vars.gage_id)
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
        run_realization(rb_cs)

    elif cfg.cycle_datetime:
        if cfg.use_hindcast:
            if cfg.hc_cold_start_state:
                raise NotImplementedError(
                    "Hindcast from cold_start_state has not yet been implemented in nwm-rte"
                )
            rb_generator = run_hindcast(
                config=cfg.mswm_InputConfig,
                valid_yaml=cfg.valid_best_yaml,
                fcst_run_name=cfg._fcst_run_name_formatted,
                cycle_interval=cfg.hc_cycle_interval,
                num_iterations=cfg.hc_num_iterations,
                cold_start_state=cfg.hc_cold_start_state,
                # This causes run_hindcast to be a generator of (yield) RealizationBuilder instances instead of running each realization itself.
                yield_realizations=True,
            )
            for i, rb in enumerate(rb_generator):
                LOG.info(f"About to run ngen for iteration {i} of hindcast workflow")
                cfg.configure_ngen_log(rb)
                run_realization(rb)
        else:
            rb_fcst = build_realization(
                cfg.mswm_RealizationBuilder_kwargs | {"use_cold_start": False},
                "build_fcst_realization",
            )
            cfg.configure_ngen_log(rb_fcst)
            run_realization(rb_fcst)

    else:
        raise ValueError(
            "Neither --cold_start_datetime nor --cycle_datetime were provided."
        )


def main(cfg: RTEForecastConfig):
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
