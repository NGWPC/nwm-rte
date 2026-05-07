"""
Command-line executable to build and run a "calibration" realization.

This runs inside the ngen runtime environment.
The CLI structure is mimicked in part by `configs.RTECalibConfig`.
For settings that are not exposed by CLI arguments, see primarily `consts.py`.

See `run_calib.sh` for example calls.
"""

import argparse
import functools
import subprocess
import time

import cli_args
import consts as c
import utils_testing_setup
from configs import CalibTimeWindows, RTECalibConfig
from execution_tests import (
    get_test_configs__calibration,
)
from mswm.build_inputs import RealizationBuilder
from utils import (
    configure_ngen_log,
    datetime_from_str,
    effective_days_from_timedelta,
    get_calibration_log_file_overwrite_path,
    str_from_datetime,
    timedelta_from_effective_days,
    timedelta_from_pandas_str,
)

print = functools.partial(print, flush=True)


def calibration__build_and_run(cfg: RTECalibConfig) -> None:
    """Build calibration realizations and run them as tests."""

    windows = CalibTimeWindows(
        calib_sim_start=cfg.calib_sim_start,
        calib_sim_duration=cfg.duration,
        calib_eval_delayment=cfg.calib_eval_delayment,
        valid_sim_advancement=cfg.valid_sim_advancement,
        valid_eval_curtailment=cfg.valid_eval_curtailment,
    )

    all_config_overrides = get_test_configs__calibration(
        nprocs=cfg.nprocs,
        gage_id=cfg.gage_id,
        hydrofab_file=cfg.hydrofab_file,
        obj_func=cfg.objective_function,
        optim_algo=cfg.optimization_algorithm,
        model_formulation=cfg.model_formulation,
        model_formulations_file=None,
        forcing_config_types=[cfg.forcing_source],
        global_domain=cfg.global_domain,
        forcing_static_dir=cfg.forcing_static_dir,
        windows=windows,
        run_type="calibration",
    )
    assert (
        len(all_config_overrides) == 1
    )  # Can be > 1 in test runner, not in atomic calibration runner
    config_overrides = all_config_overrides[0]

    rb_kwargs = {"config_overrides": config_overrides}
    rb = RealizationBuilder(**rb_kwargs)

    if cfg.forcing_source not in c.CALIB_FORCING_CONFIGURATION_TYPES:
        raise ValueError(
            f"cfg.default_realization = {cfg.default_realization} (calibration), but cfg.forcing_source {cfg.forcing_source} not in c.CALIB_FORCING_CONFIGURATION_TYPES {c.CALIB_FORCING_CONFIGURATION_TYPES}"
        )
    rb.build_calib_realization()
    log_path = get_calibration_log_file_overwrite_path(rb)
    cmd = [
        "calibration",
        str(rb.calib_config_file),
        "--log_path_overwrite",
        log_path,
    ]
    if cfg.worker_name:
        cmd.extend(["--worker_name", cfg.worker_name])
    cwd = None
    msg_suffix = f" Log path: {log_path}"

    configure_ngen_log(rb.work_dir, "cal")
    print(
        f"\n\nStarting calibration with configuration: {cfg.model_dump_json(indent=2)}\n\nvia command args: {cmd} with cwd={cwd}.{msg_suffix}"
    )
    start = time.perf_counter()
    proc = subprocess.run(cmd, check=False, cwd=cwd)
    print(
        f"\nFinished calibration with configuration: {cfg.model_dump_json(indent=2)},\nfinished in {((time.perf_counter() - start) / 60):.1f} minutes.\nReturn code {proc.returncode}.\nCommand was: {cmd}, with cwd={cwd}.{msg_suffix}"
    )
    proc.check_returncode()


def main(cfg: RTECalibConfig):
    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()
    calibration__build_and_run(cfg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script for building and running calibration realizations using historical / retrospective forcing.",
        formatter_class=argparse.RawTextHelpFormatter,
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
        "-start",
        "--calib_sim_start",
        type=datetime_from_str,
        default=str_from_datetime(c.CALIB_SIM_START_DEFAULT),
        help=f"Start time for calibration. Default={str_from_datetime(c.CALIB_SIM_START_DEFAULT)},",
    )
    parser.add_argument(
        "-evaldelay",
        "--calib_eval_delayment",
        type=timedelta_from_pandas_str,
        default=c.CALIB_EVAL_DELAYMENT_DEFAULT,
        help=f"Pandas-style timedelta string. Default={c.CALIB_EVAL_DELAYMENT_DEFAULT}",
    )
    parser.add_argument(
        "-validadvance",
        "--valid_sim_advancement",
        type=timedelta_from_pandas_str,
        default=c.VALID_SIM_ADVANCEMENT_DEFAULT,
        help=f"Pandas-style timedelta string. Default={c.VALID_SIM_ADVANCEMENT_DEFAULT}",
    )
    parser.add_argument(
        "-evalcurtail",
        "--valid_eval_curtailment",
        type=timedelta_from_pandas_str,
        default=c.VALID_EVAL_CURTAILMENT_DEFAULT,
        help=f"Pandas-style timedelta string. Default={c.VALID_EVAL_CURTAILMENT_DEFAULT}",
    )
    parser.add_argument(
        "-fsrc",
        "--forcing_source",
        type=str,
        default=c.CALIB_FORCING_CONFIGURATION_TYPE_DEFAULT,
        choices=c.CALIB_FORCING_CONFIGURATION_TYPES,
        help=f"Source of forcing data. Default={c.CALIB_FORCING_CONFIGURATION_TYPE_DEFAULT}. Choices for calibration: {c.CALIB_FORCING_CONFIGURATION_TYPES}",
    )
    parser.add_argument(
        "-fstatic",
        "--forcing_static_dir",
        type=str,
        default=c.FORCING_STATIC_DIR_DEFAULT,
        help=f"Directory for static forcing files, used when forcing_provider is 'bmi'. Default={c.FORCING_STATIC_DIR_DEFAULT}",
    )
    parser.add_argument(
        "-wrkr",
        "--worker_name",
        type=str,
        help="If provided, will be used as the worker name, instead of letting cal mgr choose a random worker name. Only allowed for Optimization Algorithm DDS, which uses single instances of ngen. Does not affect 'default' realization (which is not a calibration).",
    )
    parser.add_argument(
        "--hydrofab_file",
        type=str,
        default=None,
        help="Path to local hydrofabric gpkg file. If provided, bypasses msw-mgr Icefabric API call.",
    )
    cli_args.add_args_for_script(parser, cli_args.Script.CALIBRATION)
    args = parser.parse_args()
    cfg = RTECalibConfig(**vars(args))
    main(cfg)
