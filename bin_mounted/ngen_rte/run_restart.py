"""
Command-line executable to restart a failed run from a saved checkpoint. Currently only functional for default and regionalization runs.
Calls msw-mgr chcekpoint_restart to copy and configure the run, then infers the ngen command from the destination directory.
A run can only be restarted if the original run was configured to save checkpoints using the --checkpoint_interval argument.
"""

import argparse
import functools
import json
from pathlib import Path

from mswm.utils.checkpoint_restart import checkpoint_restart
from mswm.build_inputs import RealizationBuilder

from ngen_rte.configs import RTEAsyncConfig
from ngen_rte.execution.ngen_async import NgenRunnerAsync
from ngen_rte.run_config import cli_args

print = functools.partial(print, flush=True)


def infer_gage_id(src_path: str) -> str:
    """Infer gage ID from source run directory path"""
    return Path(src_path).resolve().name


def infer_rb(dst_path: str, src_path: str) -> RealizationBuilder:
    """Infer and return a minimal RealizationBuilder from the destination directory structure"""
    dst = Path(dst_path).resolve()
    input_dir = dst / "Input"

    ngen_bin = input_dir / "ngen"
    if not ngen_bin.exists():
        raise FileNotFoundError(f"ngen binary not found at: {ngen_bin}")

    realization_files = list(dst.rglob("*realization*.json"))
    if not realization_files:
        raise FileNotFoundError(f"No realization file found in destination run folder: {input_dir}")
    realization_file = str(realization_files[0])

    part_files = list(input_dir.rglob("*partition*.json"))
    part_file = str(part_files[0]) if part_files else None

    rb = RealizationBuilder.__new__(RealizationBuilder)
    rb.realization_file = realization_file
    rb.part_file = part_file
    rb.work_dir = str(dst)
    rb.valid_yaml = None
    rb.run_type = "default"
    rb.basin = infer_gage_id(src_path)
    return rb


def infer_nprocs(rb: RealizationBuilder) -> int:
    """Infer nprocs from the partition file, defaulting to 1 if not present"""
    if rb.part_file is None:
        return 1
    with open(rb.part_file) as f:
        partitions = json.load(f)
    return len(partitions.get("partitions", []))


def run_restart(src_path: str, dst_path: str, checkpoint_state_path: str) -> str:
    """
    Call checkpoint_restart, then execute the ngen run from the destination path

    Returns the path to the ngen stdout + stderr log file
    """

    checkpoint_restart(
        src_path=src_path,
        dst_path=dst_path,
        checkpoint_state_path=checkpoint_state_path,
    )

    rb = infer_rb(dst_path, src_path)

    cfg = RTEAsyncConfig(
        nprocs=infer_nprocs(rb),
    )
    cfg.configure_ngen_log(rb)

    print(f"\nStarting restart run from: {dst_path}")
    ngen_runner = NgenRunnerAsync(cfg=cfg, rb=rb, postprocess=False)
    ngen_runner.start()
    ngen_runner.stream_status_until_complete()
    ngen_runner.close()


def cli_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restart a default ngen realization from a checkpoint.",
        formatter_class=cli_args.HelpFormatter,
    )
    parser.add_argument("--src_path", "-src", required=True, help="Path to the existing run to restart from.")
    parser.add_argument("--dst_path", "-dst", required=True, help="Path to the new restart run destination. Defaults to src_path + '_restart'.")
    parser.add_argument("--checkpoint_state_path", "-csp", required=True, help="Path to the checkpoint state folder.")
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    run_restart(
        src_path=args.src_path,
        dst_path=args.dst_path,
        checkpoint_state_path=args.checkpoint_state_path,
    )
