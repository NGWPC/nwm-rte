"""
Command-line executable to build and run a "default" realization. Supports realtime forcing configurations, e.g. `"short_range"`, as well as historical/retrospective sources, e.g. `"aorc"`.

This runs inside the ngen runtime environment.
The CLI structure is mimicked in part by `configs.RTEDefaultConfig`.
For settings that are not exposed by CLI arguments, see primarily `consts.py`.

See `run_default.sh` for example calls.
"""

import argparse
import functools
import os
import shutil
import subprocess
import time

from mswm.build_inputs import RealizationBuilder

import cli_args
from utils import (
    timedelta_from_effective_days,
    configure_ngen_log,
    datetime_type,
)
import utils_testing_setup
import consts as c
from configs import RTEDefaultConfig

print = functools.partial(print, flush=True)


def build_default_realization(cfg: RTEDefaultConfig) -> RealizationBuilder:
    """Build and return a non-coldstart forecast realization"""
    print("Building default realization...")
    rb = RealizationBuilder(**cfg.realization_builder_kwargs)
    rb.build_default_realization()
    configure_ngen_log(rb.work_dir, "default")
    return rb


def get_ngen_cmd(cfg: RTEDefaultConfig, rb: RealizationBuilder) -> list[str]:
    """Build and return the ngen command as a list of strings.
    rb must have already been built, e.g. rb.build_default_realization() already called."""
    cmd = [
        os.path.join(rb.input_dir, "ngen"),
        rb.cat_file,
        "all",
        rb.nexus_file,
        "all",
        rb.realization_file,
    ]
    if cfg.nprocs > 1:
        cmd = ["mpirun", "-n", f"{cfg.nprocs}"] + cmd + [rb.part_file]
    return cmd


def run_default(
    rb: RealizationBuilder,
    cfg: RTEDefaultConfig,
    clear_output_dir: bool = False,
) -> str:
    """Run the provided default realization.
    Realization should already be built (rb.build_default_realization() already called).

    If clear_output_dir, the contents of the output dir will be deleted (recursively) before running the realization.

    Returns: The path to the ngen stdout + stderr log file.
    """
    ngen_log_description = "default"
    output_dir = os.path.join(rb.work_dir, "Output", "Default_Run", cfg.fcst_run_name)

    if clear_output_dir and os.path.exists(output_dir):
        print(f"Deleting output dir: {output_dir}")
        shutil.rmtree(output_dir)

    cwd = output_dir
    output_ngen_stdout_stderr_log = os.path.join(
        output_dir, c.NGEN_STDOUT_STDERR_LOG_FILE_BASENAME
    )
    cmd = get_ngen_cmd(cfg, rb)

    print(
        f"\n\nStarting {ngen_log_description} with configuration: {cfg.model_dump_json(indent=2)}\n\nvia command args: {cmd} with cwd={cwd}."
    )
    start = time.perf_counter()
    os.makedirs(output_dir, exist_ok=True)
    with open(output_ngen_stdout_stderr_log, "a+") as f:
        proc = subprocess.run(cmd, check=False, cwd=cwd, stdout=f, stderr=f)
    print(
        f"\nFinished {ngen_log_description} with configuration: {cfg.model_dump_json(indent=2)},\nfinished in {((time.perf_counter() - start) / 60):.1f} minutes.\nReturn code {proc.returncode}.\nCommand was: {cmd}, with cwd={cwd}."
    )
    proc.check_returncode()
    return output_ngen_stdout_stderr_log


def main(cfg: RTEDefaultConfig):
    # util_asserts.assert_paths__core(forecast_vars.gage_id)
    # util_asserts.assert_paths__raw_config()
    # util_asserts.assert_paths_common_input()

    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()

    rb = build_default_realization(cfg)
    print(f"Running default realization: {rb.input_configs['Forcing']}")
    run_default(rb, cfg)


def cli_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="""Script for building and running default realizations
        using realtime forcing configurations or historical / retrospective forcing.
        The CLI arguments mostly follow that of run_forecast.py. The exception is
        that "--historical_sim_duration" aka "-dur" (in days) was added to this script
        to support the historical / retrospective forcing use case, e.g. AORC or NWM.""",
        formatter_class=argparse.RawTextHelpFormatter,
    )
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
        "-g",
        "--gage_id",
        type=str,
        default=c.DEFAULT_GAGE_ID,
        help=f"Default gage ID. Defaults={c.DEFAULT_GAGE_ID}",
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
        help=f"Forcing provider to use, e.g., 'bmi'. Default: {repr(c.FORCING_PROVIDER_DEFAULT)}",
        default=c.FORCING_PROVIDER_DEFAULT,
    )
    parser.add_argument(
        "-dt",
        "--cycle_datetime",
        required=True,
        type=datetime_type,
        help="Start date/time for the simulation.",
    )
    parser.add_argument(
        "-dur",
        "--historical_sim_duration",
        type=timedelta_from_effective_days,
        default=None,
        help=f"Only used for historical / retrospective forcing (required in that case). Simulation duration in days. Default={None}",
    )
    cli_args.add_arg(parser, cli_args.LAGGED_ENSEMBLE)
    parser.add_argument(
        "-fconfig",
        "--forcing_configuration",
        type=str,
        help=f"Forcing configuration to use, e.g., 'short_range', 'standard_ana', 'aorc', etc. Default: {repr(c.FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT[0])}",
        default=c.FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT[0],
        choices=c.ALL_FORCING_CONFIGURATION_TYPES,
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
        help=f"""Number of processors. Default={repr(c.DEFAULT_NPROCS)})""",
        default=c.DEFAULT_NPROCS,
    )
    parser.add_argument(
        "--hydrofab_file",
        type=str,
        default=None,
        help="Path to local hydrofabric gpkg file. If provided, bypasses msw-mgr Icefabric API call."
    )
    cli_args.add_arg(parser, cli_args.MODELS_CSV)
    cli_args.add_arg(parser, cli_args.MODELS_RZ)
    cli_args.add_arg(parser, cli_args.TIMESTAMP_RUN_NAME_SUFFIX)
    cli_args.add_arg(parser, cli_args.NWM_OUTPUT_VARIABLES)
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    cfg = RTEDefaultConfig(**vars(args))
    main(cfg)
