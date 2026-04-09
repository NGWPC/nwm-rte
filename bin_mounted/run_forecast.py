import functools
import argparse

from mswm.build_inputs import RealizationBuilder
from nwm_fcst_mgr.forecast import (
    run_forecast as run_fcst,
    run_lagged_ensemble,
    LAGGED_ENSEMBLE_MEMBER_0,
)

import consts as c
from configs import RTEForecastConfig
import utils_testing_setup
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


def build_run_coldstart_realization(cfg: RTEForecastConfig) -> RealizationBuilder:
    """Build and run a coldstart forecast realization."""
    rb_kwargs_final = cfg.realization_builder_kwargs | {"use_cold_start": True}
    rb = build_realization(cfg, rb_kwargs_final, "cs")
    run_realization(rb, cfg)
    return rb


def build_run_forecast_realization(cfg: RTEForecastConfig) -> RealizationBuilder:
    """Build and return a non-coldstart forecast realization."""
    if cfg.lagged_ensemble:
        lagged_ens_mem = LAGGED_ENSEMBLE_MEMBER_0
    else:
        lagged_ens_mem = None

    rb_kwargs_final = cfg.realization_builder_kwargs | {
        "use_cold_start": False,
        "use_lagged_ens": cfg.lagged_ensemble,
        "lagged_ens_mem": lagged_ens_mem,
    }

    rb = build_realization(cfg, rb_kwargs_final, "fcst")
    run_realization(rb, cfg)
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

    if rb.use_lagged_ens:
        print(f"Calling: {run_lagged_ensemble}")
        run_lagged_ensemble(
            input_path=None,
            valid_yaml=cfg.valid_best_yaml,
            fcst_run_name=cfg.fcst_run_name,
            open_loop_state=cfg.le__open_loop_state,
            closed_loop_state=cfg.le__closed_loop_state,
            partition_file=rb.part_file,
            config_overrides=rb.config_overrides,
        )
        print(f"Finished calling: {run_lagged_ensemble}")
    elif rb.use_hindcast:
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
        rb_cs = build_run_coldstart_realization(cfg)
        run_realization(rb_cs, cfg)
    if cfg.cycle_datetime:
        rb_fcst = build_run_forecast_realization(cfg)
        run_realization(rb_fcst, cfg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-delscratch",
        "--delete_scratch_and_mesh_first",
        action="store_true",
        help="Delete scratch dir and ESMF mesh files before the run, which forces ESMF and NetCDF actions to occur.",
    )
    parser.add_argument(
        "-delraw",
        "--delete_forcing_raw_input_first",
        action="store_true",
        help=f"Delete contents of {repr(c.DIR_FORCING_RAW_INPUT)} before the run, which forces forcing data to be re-downloaded.",
    )
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
        "-g",
        "--gage_id",
        type=str,
        help=f"Gage ID to run the forecast for. Default: {repr(c.DEFAULT_GAGE_ID)}",
        default=c.DEFAULT_GAGE_ID,
    )
    parser.add_argument(
        "-gdomain",
        "--global_domain",
        type=str,
        default=c.CALIB_GLOBAL_DOMAIN_DEFAULT,
        choices=c.CALIB_GLOBAL_DOMAIN_CHOICES,
        help=f"Global domain/region of forcing data. Default={c.CALIB_GLOBAL_DOMAIN_DEFAULT}",
    )
    parser.add_argument(
        "-fstatic",
        "--forcing_static_dir",
        type=str,
        default=c.FORCING_STATIC_DIR_DEFAULT,
        help=f"Directory for static forcing files, used when forcing_provider is 'bmi'. Default={c.FORCING_STATIC_DIR_DEFAULT}",
    )
    parser.add_argument(
        "-fprov",
        "--forcing_provider",
        type=str,
        help=f"Forcing provider to use, e.g., 'bmi' or 'csv'. Default: {repr(c.FORCING_PROVIDER_DEFAULT)}",
        default=c.FORCING_PROVIDER_DEFAULT,
    )
    parser.add_argument(
        "-dt",
        "--cycle_datetime",
        type=datetime_type,
        help="For a regular forecast, this is the start time. When cold-start is used, this is the *end* of the cold-start cycle. Format: 'YYYY-MM-DD HH:mm:ss'.",
        required=True,
    )
    parser.add_argument(
        "-csdt",
        "--cold_start_datetime",
        type=datetime_type,
        help="If provided, a cold-start realization will be ran prior to the forecast, and this value will be the start time for the cold-start. Format: 'YYYY-MM-DD HH:mm:ss'.",
        default=None,
    )
    parser.add_argument(
        "-le",
        "--lagged-ensemble",
        dest="le__open_loop_state__closed_loop_state",
        type=str,
        nargs=2,
        help="""If provided, a lagged ensemble will be performed. Only for the regular forecast (non-cold-start).
                This takes 2 optional arguments: open_loop_state, closed_loop_state.
                Each optional argument is a file path. See nwm-fcst-mgr function `run_lagged_ensemble` for details.
                To run a lagged ensemble without these args, provide them as empty strings e.g. `-le '' ''`.""",
    )
    parser.add_argument(
        "-fconfig",
        "--forcing_configuration",
        type=str,
        help=f"Forcing configuration to use, e.g., 'short_range', 'standard_ana', etc. Default: {repr(c.FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT[0])}",
        default=c.FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT[0],
    )
    parser.add_argument(
        "-rname",
        "--fcst_run_name",
        type=str,
        help=f"Forecast run name. Default: {repr(c.DEFAULT_FORECAST_RUN_NAME)}",
        default=c.DEFAULT_FORECAST_RUN_NAME,
    )
    parser.add_argument(
        "-n",
        "--nprocs",
        type=int,
        default=c.DEFAULT_NPROCS,
        help=f"""Replaces default value for nprocs ({repr(c.DEFAULT_NPROCS)}) and subsequently the ParallelConfig instance that is passed to MSWM.""",
    )
    args = parser.parse_args()
    cfg = RTEForecastConfig(**vars(args))
    main(cfg)
