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

import cli_args
import consts as c
import utils_testing_setup
from configs import RTEDefaultConfig
from mswm.build_inputs import RealizationBuilder
from utils import configure_ngen_log

print = functools.partial(print, flush=True)


def build_default_realization(cfg: RTEDefaultConfig) -> RealizationBuilder:
    """Build and return a non-coldstart forecast realization"""
    print("Building default realization...")
    rb = RealizationBuilder(**cfg.mswm_RealizationBuilder_kwargs)
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
    output_dir = os.path.join(rb.work_dir, "Output", "Default_Run", cfg._fcst_run_name)

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
