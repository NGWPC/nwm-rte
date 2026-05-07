"""
Command-line executable to build and run a "forecast" realization, optionally with a coldstart.

This runs inside the ngen runtime environment.
The CLI structure is mimicked in part by `configs.RTEForecastConfig`.
For settings that are not exposed by CLI arguments, see primarily `consts.py`.

See `run_fcst.sh` for example calls.
"""

import argparse
import functools

import cli_args
import consts as c
import utils_testing_setup
from configs import RTEForecastConfig
from mswm.build_inputs import RealizationBuilder
from nwm_fcst_mgr.forecast import (
    run_forecast as run_fcst,
)
from utils import configure_ngen_log, datetime_type

print = functools.partial(print, flush=True)


def build_realization(
    cfg: RTEForecastConfig,
    rb_kwargs_final: dict,
    log_label: str,
) -> RealizationBuilder:
    """Build and return a forecast realization, applygin the provided rb_kwargs_final as-is."""
    print(f"Building realization: {rb_kwargs_final}")
    rb = RealizationBuilder(**rb_kwargs_final)
    rb.build_fcst_realization()
    configure_ngen_log(rb.input_dir, log_label)
    print(f"Wrote: {rb.realization_file}")
    if cfg.nprocs > 1 and not rb.part_file:
        raise ValueError(
            f"Expected partition file since cfg.nprocs > 1 ({cfg.nprocs}), but it is {repr(rb.part_file)}"
        )
    return rb


def build_coldstart_realization(cfg: RTEForecastConfig) -> RealizationBuilder:
    """Build and return a coldstart forecast realization."""
    rb_kwargs_final = cfg.realization_builder_kwargs | {"use_cold_start": True}
    rb = build_realization(cfg, rb_kwargs_final, "cs")
    return rb


def build_forecast_realization(cfg: RTEForecastConfig) -> RealizationBuilder:
    """Build and return a non-coldstart forecast realization."""
    rb_kwargs_final = cfg.realization_builder_kwargs | {
        "use_cold_start": False,
    }

    rb = build_realization(cfg, rb_kwargs_final, "fcst")
    return rb


def run_realization(
    rb: RealizationBuilder,
    cfg: RTEForecastConfig,
) -> None:
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
        print(f"Calling: {run_fcst}")
        run_fcst(
            valid_yaml=cfg.valid_best_yaml,
            real_path=str(rb.realization_file),
            partition_file=rb.part_file,
        )
        print(f"Finished calling: {run_fcst}")


def main(cfg: RTEForecastConfig):
    # util_asserts.assert_paths__core(forecast_vars.gage_id)
    # util_asserts.assert_paths__raw_config()
    # util_asserts.assert_paths_common_input()

    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()

    if not (cfg.cold_start_datetime or cfg.cycle_datetime):
        raise ValueError(
            "Must provide --cold_start_datetime or --cycle_datetime or both, but neither were provided."
        )

    if cfg.cold_start_datetime:
        rb_cs = build_coldstart_realization(cfg)
        run_realization(rb_cs, cfg)
    if cfg.cycle_datetime:
        rb_fcst = build_forecast_realization(cfg)
        run_realization(rb_fcst, cfg)


def cli_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser"""
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "-ofunc",
        "--objective_function",
        type=c.CalObjective,
        default=c.CALIB_OBJECTIVE_FUNCTION,
        help=f"Objective function of previously-ran calibration realization for basis of forecast. Affects directory path. Default: {c.CALIB_OBJECTIVE_FUNCTION}",
    )
    parser.add_argument(
        "-optalgo",
        "--optimization_algorithm",
        type=c.CalOptimizationAlgo,
        default=c.CALIB_OPTIMIZATION_ALGO,
        help=f"Optimization algorithm of previously-ran calibration realization for basis of forecast. Affects directory path. Default: {c.CALIB_OPTIMIZATION_ALGO}",
    )
    parser.add_argument(
        "-fstatic",
        "--forcing_static_dir",
        type=str,
        default=c.FORCING_STATIC_DIR_DEFAULT,
        help=f"Directory for static forcing files, used when forcing_provider is 'bmi'. Default={c.FORCING_STATIC_DIR_DEFAULT}",
    )
    parser.add_argument(
        "-csdt",
        "--cold_start_datetime",
        type=datetime_type,
        help="If provided, a cold-start realization will be ran prior to the forecast, and this value will be the start time for the cold-start. Format: 'YYYY-MM-DD HH:mm:ss'.",
        default=None,
    )
    cli_args.add_args_for_script(parser, cli_args.Script.FORECAST)
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    cfg = RTEForecastConfig(**vars(args))
    main(cfg)
