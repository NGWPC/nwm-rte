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

from mswm.build_inputs import RealizationBuilder

from ngen_rte import consts as c
from ngen_rte.configs import RTECalibConfig

# from ngen_rte.execution.ngen_logs import NgenLogsParser
from ngen_rte.run_config import cli_args
from ngen_rte.tests import utils_testing_setup
from ngen_rte.utils import configure_ngen_log, get_calibration_log_file_overwrite_path

print = functools.partial(print, flush=True)


def build_calibration(cfg: RTECalibConfig) -> RealizationBuilder:
    """Build calibration realization and return a RealizationBuilder instance."""
    rb = RealizationBuilder(**cfg.mswm_RealizationBuilder_kwargs)

    if cfg.forcing_configuration not in c.CALIB_FORCING_TYPES:
        raise ValueError(
            f"cfg.default_realization = {cfg.default_realization} (calibration), but cfg.forcing_configuration {cfg.forcing_configuration} not in c.CALIB_FORCING_TYPES {c.CALIB_FORCING_TYPES}"
        )
    rb.build_calib_realization()
    return rb


def get_calibration_cmd(
    rb: RealizationBuilder, worker_name: str, log_path: str
) -> list[str]:
    """Get the command to run the calibration realization."""
    cmd = [
        "calibration",
        str(rb.calib_config_file),
        "--log_path_overwrite",
        log_path,
    ]
    if worker_name:
        cmd.extend(["--worker_name", worker_name])
    return cmd


def run_calibration(cfg, rb: RealizationBuilder) -> None:
    log_path = get_calibration_log_file_overwrite_path(rb)
    cmd = get_calibration_cmd(rb, cfg.worker_name, log_path)
    cwd = None
    msg_suffix = f" Log path: {log_path}"

    configure_ngen_log(rb.work_dir, "cal")
    start = time.perf_counter()

    # ngen_parser = NgenLogsParser(cfg=cfg, rb=rb)
    print(
        f"\n\nStarting calibration with configuration: {cfg.model_dump_json(indent=2)}\n\nvia command args: {cmd} with cwd={cwd}.{msg_suffix}"
    )
    proc = subprocess.run(cmd, check=False, cwd=cwd)
    print(
        f"\nFinished calibration with configuration: {cfg.model_dump_json(indent=2)},\nfinished in {((time.perf_counter() - start) / 60):.1f} minutes.\nReturn code {proc.returncode}.\nCommand was: {cmd}, with cwd={cwd}.{msg_suffix}"
    )
    # ngen_parser.log_all_payloads()

    proc.check_returncode()


def main(cfg: RTECalibConfig):
    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()
    rb = build_calibration(cfg)
    run_calibration(cfg, rb)


def cli_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="""Script for building and running a calibration
realization using historical / retrospective forcing.""",
        formatter_class=cli_args.HelpFormatter,
    )
    cli_args.add_args_for_script(parser, cli_args.Script.CALIBRATION)
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    main(cfg=RTECalibConfig(**vars(args)))
