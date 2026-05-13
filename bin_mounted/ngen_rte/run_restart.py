"""
Command-line executable to restart a failed run from a saved checkpoint. Currently only functional for default and regionalization runs.
Calls msw-mgr chcekpoint_restart to copy and configure the run, then infers the ngen command from the destination directory.
A run can only be restarted if the original run was configured to save checkpoints using the --checkpoint_interval argument.
"""

import argparse
import functools
import json
import os
import subprocess
import time
from pathlib import Path

from mswm.utils.checkpoint_restart import checkpoint_restart

from ngen_rte import consts as c
from ngen_rte.run_config import cli_args

print = functools.partial(print, flush=True)


def infer_ngen_cmd(dst_path: str) -> list[str]:
    """Infer and return the ngen command based on the destination directory structure"""
    dst = Path(dst_path).resolve()

    input_dir = dst / "Input"
    ngen_bin = input_dir / "ngen"
    if not ngen_bin.exists():
        raise FileNotFoundError(f"ngen binary not found at: {ngen_bin}")

    gpkg_files = list(input_dir.glob("*.gpkg"))
    if not gpkg_files:
        raise FileNotFoundError(f"No .gpkg file found in destination run folder: {input_dir}")
    gpkg_file = str(gpkg_files[0])

    realization_files = list(dst.rglob("*realization*.json"))
    if not realization_files:
        raise FileNotFoundError(f"No realization file found in destination run folder: {input_dir}")
    realization_file = str(realization_files[0])

    # Construct ngen run command
    cmd = [str(ngen_bin), gpkg_file, "all", gpkg_file, "all", realization_file]

    # Refactor run command if partition was used
    part_files = list(input_dir.rglob("*partition*.json"))
    if part_files:
        part_file = str(part_files[0])
        with open(part_file) as f:
            partitions = json.load(f)
        nprocs = len(partitions.get("partitions", []))
        cmd = ["mpirun", "-n", str(nprocs)] + cmd + [part_file]

    return cmd


def run_restart(src_path: str, dst_path: str, checkpoint_state_path: str, output_name: str) -> str:
    """
    Call checkpoint_restart, then execute the ngen run from the destination path

    Returns the path to the ngen stdout + stderr log file
    """
    print(f"Running checkpoint_restart: {src_path} -> {dst_path}")
    checkpoint_restart(
        src_path=src_path,
        dst_path=dst_path,
        checkpoint_state_path=checkpoint_state_path,
    )

    cmd = infer_ngen_cmd(dst_path)

    # TODO: Not entirely sure how to handle the output directory on a restart, since we don't have easy access to the formatted forecast name
    output_dir = os.path.join(dst_path, "Output", "Default_Run", output_name)
    os.makedirs(output_dir, exist_ok=True)
    ngen_log = os.path.join(output_dir, c.NGEN_STDOUT_STDERR_LOG_FILE_BASENAME)

    print(f"\nStarting restart run via command: {cmd}, cwd={output_dir}")
    start = time.perf_counter()
    with open(ngen_log, "a+") as f:
        proc = subprocess.run(cmd, check=False, cwd=output_dir, stdout=f, stderr=f)
    print(
        f"\nFinished restart run in {((time.perf_counter() - start) / 60):.1f} minutes."
        f"\nReturn code {proc.returncode}.\nCommand was: {cmd}, cwd={output_dir}."
    )
    proc.check_returncode()
    return ngen_log


def cli_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restart a default ngen realization from a checkpoint.",
        formatter_class=cli_args.HelpFormatter,
    )
    parser.add_argument("--src_path", "-src", required=True, help="Path to the existing run to restart from.")
    parser.add_argument("--dst_path", "-dst", required=True, help="Path to the new restart run destination. Defaults to src_path + '_restart'.")
    parser.add_argument("--checkpoint_state_path", "-csp", required=True, help="Path to the checkpoint state folder.")
    parser.add_argument("--output_name", "-oname", required=True, help="Name for the restart run output directory.")
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    run_restart(
        src_path=args.src_path,
        dst_path=args.dst_path,
        checkpoint_state_path=args.checkpoint_state_path,
        output_name=args.output_name
    )
