import argparse
import functools
import subprocess
import time

from mswm.build_inputs import RealizationBuilder

from utils import (
    datetime_from_str,
    str_from_datetime,
    timedelta_from_effective_days,
    effective_days_from_timedelta,
    timedelta_from_pandas_str,
    get_calibration_log_file_overwrite_path,
)
import utils_testing_setup
from execution_tests import (
    get_test_configs__calibration,
    make_parallel_config,
)
import consts as c
from configs import RTECalibConfig, CalibTimeWindows

print = functools.partial(print, flush=True)


def calibration__build_and_run(cfg: RTECalibConfig) -> None:
    """Build calibration realizations and run them as tests."""

    windows = CalibTimeWindows(
        calib_sim_start=cfg.calib_sim_start,
        calib_sim_duration=cfg.calib_sim_duration,
        calib_eval_delayment=cfg.calib_eval_delayment,
        valid_sim_advancement=cfg.valid_sim_advancement,
        valid_eval_curtailment=cfg.valid_eval_curtailment,
    )

    all_config_overrides = get_test_configs__calibration(
        nprocs=cfg.nprocs,
        gage_id=cfg.gage_id,
        gage_vintage=cfg.gage_vintage,
        obj_func=cfg.objective_function,
        optim_algo=cfg.optimization_algorithm,
        forcing_config_types=[cfg.forcing_source],
        global_domain=cfg.global_domain,
        forcing_provider=cfg.forcing_provider,
        forcing_static_dir=cfg.forcing_static_dir,
        windows=windows,
        obs_dir=cfg.obs_dir,
        nwmretro_file=cfg.nwmretro_file,
    )
    assert (
        len(all_config_overrides) == 1
    )  # Can be > 1 in test runner, not in atomic calibration runner
    config_overrides = all_config_overrides[0]

    rb_kwargs = {"config_overrides": config_overrides}
    rb = RealizationBuilder(**rb_kwargs)
    rb.build_calib_realization()

    log_path = get_calibration_log_file_overwrite_path(rb)
    cmd = [
        "calibration",
        str(rb.calib_config_file),
        "--log_path_overwrite",
        log_path,
        # "--worker_name",
        # "000test",
    ]

    print(
        f"\n\nStarting calibration with configuration: {cfg.model_dump_json(indent=2)}\nand logging to: {log_path}\n\nvia command args: {cmd}"
    )
    start = time.perf_counter()
    proc = subprocess.run(cmd, check=False)
    print(
        f"\nFinished calibration with configuration: {cfg.model_dump_json(indent=2)},\nfinished in {((time.perf_counter() - start) / 60):.1f} minutes.\nLog path: {log_path}\nReturn code {proc.returncode}."
    )
    proc.check_returncode()


def main(cfg: RTECalibConfig):
    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()

    calibration__build_and_run(cfg)


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
        "-n",
        "--nprocs",
        type=int,
        default=c.DEFAULT_NPROCS,
        help=f"""
Currently only affects Calibration. Replaces default value for nprocs ({repr(c.DEFAULT_NPROCS)}) and subsequently the ParallelConfig instance.
When nprocs is 1, Calibration's ParallelConfig is: {make_parallel_config(nprocs=1)}.
When nprocs > 1, Calibration's ParallelConfig is like: {make_parallel_config(nprocs=2)}
""",
    )
    parser.add_argument(
        "-g",
        "--gage_id__gage_vintage",
        type=str,
        nargs=2,
        default=[c.DEFAULT_GAGE_ID, c.DEFAULT_GAGE_VINTAGE],
        help=f"Calibration gage ID and gage vintage (2 args). Defaults={c.DEFAULT_GAGE_ID}, {c.DEFAULT_GAGE_VINTAGE}",
    )
    parser.add_argument(
        "-start",
        "--calib_sim_start",
        type=datetime_from_str,
        default=str_from_datetime(c.CALIB_SIM_START_DEFAULT),
        help=f"Start time for calibration. Default={str_from_datetime(c.CALIB_SIM_START_DEFAULT)},",
    )
    parser.add_argument(
        "-dur",
        "--calib_sim_duration",
        type=timedelta_from_effective_days,
        default=c.CALIB_SIM_DURATION_DEFAULT,
        help=f"Duration of calibration, in days (provide integer). Default={effective_days_from_timedelta(c.CALIB_SIM_DURATION_DEFAULT)}",
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
        help=f"Source of forcing data. Default={c.CALIB_FORCING_CONFIGURATION_TYPE_DEFAULT}",
    )
    parser.add_argument(
        "-gdomain",
        "--global_domain",
        type=str,
        default=c.CALIB_GLOBAL_DOMAIN_DEFAULT,
        choices=c.CALIB_GLOBAL_DOMAIN_CHOICES,
        help=f"Region of forcing data. Default={c.CALIB_GLOBAL_DOMAIN_DEFAULT}",
    )
    parser.add_argument(
        "-fprovider",
        "--forcing_provider",
        type=str,
        default=c.FORCING_PROVIDER_DEFAULT,
        choices=c.FORCING_PROVIDER_CHOICES,
        help=f"Forcing provider. Default={c.FORCING_PROVIDER_DEFAULT}",
    )
    parser.add_argument(
        "-fstatic",
        "--forcing_static_dir",
        type=str,
        default=c.FORCING_STATIC_DIR_DEFAULT,
        help=f"Directory for static forcing files, used when forcing_provider is 'bmi'. Default={c.FORCING_STATIC_DIR_DEFAULT}",
    )
    args = parser.parse_args()
    cfg = RTECalibConfig(**vars(args))
    main(cfg)
