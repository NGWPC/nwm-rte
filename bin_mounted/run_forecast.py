import copy
from datetime import datetime
import functools
import argparse

from mswm.build_inputs import RealizationBuilder
from mswm.utils import settings as mswm_settings
from nwm_fcst_mgr.forecast import run_fcst

from execution_tests import make_parallel_config
import consts as c
from configs import RTEForecastConfig
import utils_testing_setup

print = functools.partial(print, flush=True)


def build_coldstart_realization(cfg: RTEForecastConfig) -> RealizationBuilder:
    rb_cs = RealizationBuilder(**cfg.realization_builder_kwargs, use_cold_start=True)

    cs_update = {
        "forcing_configuration": cfg.forcing_configuration,
        "cold_start_datetime": cfg.coldstart_start.strftime(
            mswm_settings.DEFAULT_DATETIME_FORMAT
        ),
        "cycle_datetime": cfg.coldstart_end.strftime(
            mswm_settings.DEFAULT_DATETIME_FORMAT
        ),
    }
    rb_kwargs = copy.deepcopy(cfg.realization_builder_kwargs)
    rb_kwargs["config_overrides"].Forcing.update(cs_update)

    print(f"Building coldstart realization: {rb_kwargs['config_overrides']}")
    rb_cs = RealizationBuilder(**rb_kwargs)
    rb_cs.build_fcst_realization()
    print(f"Wrote: {rb_cs.realization_file}")
    return rb_cs


def build_forecast_realization(cfg: RTEForecastConfig) -> RealizationBuilder:
    rb_fcst = RealizationBuilder(**cfg.realization_builder_kwargs, use_cold_start=False)
    rb_fcst.build_fcst_realization()
    return rb_fcst


def datetime_type(datetime_str) -> datetime:
    return datetime.strptime(datetime_str, mswm_settings.DEFAULT_DATETIME_FORMAT)


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
        print(f"Running coldstart realization: {rb_cs.input_configs['Forcing']}")
        run_fcst(
            valid_yaml=cfg.valid_best_yaml,
            real_path=str(rb_cs.realization_file),
        )

    if cfg.cycle_datetime:
        rb_fcst = build_forecast_realization(cfg)
        print(f"Running forecast realization: {rb_fcst.input_configs['Forcing']}")
        run_fcst(
            valid_yaml=cfg.valid_best_yaml,
            real_path=str(rb_fcst.realization_file),
        )


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
        "--skip_calibration",
        action="store_true",
        help="Causes calibration to be skipped",
    )
    parser.add_argument(
        "-ofunc",
        "--objective_function",
        type=c.CalObjective,
        default=c.CALIB_OBJECTIVE_FUNCTION,
        help=f"Objective function for calibration. Default: {c.CALIB_OBJECTIVE_FUNCTION}",
    )
    parser.add_argument(
        "-optalgo",
        "--optimization_algorithm",
        type=c.CalOptimizationAlgo,
        default=c.CALIB_OPTIMIZATION_ALGO,
        help=f"Optimization algorithm for calibration. Default: {c.CALIB_OPTIMIZATION_ALGO}",
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
        help="start date/time for the forecast cycle (also the end of cold-start if chosen), format= 'YYYY-MM-DD HH:mm:ss'. If omitted, a forecast will not be ran.",
        default=None,
    )
    parser.add_argument(
        "-csdt",
        "--cold_start_datetime",
        type=datetime_type,
        help="start date/time for cold-start, format= 'YYYY-MM-DD HH:mm:ss'. If omitted, a cold-start will not be used.",
        default=None,
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
    (
        parser.add_argument(
            "-n",
            "--nprocs",
            type=int,
            help=f"""
Currently only affects Calibration. Replaces default value for nprocs ({repr(c.DEFAULT_NPROCS)}) and subsequently the ParallelConfig instance.
When nprocs is 1, Calibration's ParallelConfig is: {make_parallel_config(nprocs=1)}.
When nprocs > 1, Calibration's ParallelConfig is like: {make_parallel_config(nprocs=2)}
""",
            default=c.DEFAULT_NPROCS,
        ),
    )
    args = parser.parse_args()
    cfg = RTEForecastConfig(**vars(args))
    main(cfg)
