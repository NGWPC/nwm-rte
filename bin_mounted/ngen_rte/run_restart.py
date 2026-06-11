"""
Command-line executable to restart a failed run from a saved checkpoint. Currently only functional for default and regionalization runs.
Calls msw-mgr chcekpoint_restart to copy and configure the run, then infers the ngen command from the destination directory.
A run can only be restarted if the original run was configured to save checkpoints using the --checkpoint_interval argument.
"""

import argparse
import json
from pathlib import Path

from mswm.utils.checkpoint_restart import checkpoint_restart
from mswm.build_inputs import RealizationBuilder

from ngen_rte.configs import RTEAsyncConfig
from ngen_rte.execution.ngen_async import NgenRunnerAsync
from ngen_rte.run_config import cli_args
from ngen_rte.logger import initialize_logger
from ngen_rte.utils import (
    _rte_transmit_job_complete,
    _rte_transmit_job_failed,
    _rte_transmit_job_start,
    transmit,
)

LOG = initialize_logger()


def infer_gage_id(src_path: str) -> str:
    """Infer gage ID from source run directory path"""
    return Path(src_path).resolve().name


def infer_rb(dst_path: str, src_path: str) -> RealizationBuilder:
    """Infer and return a minimal RealizationBuilder from the destination directory structure"""
    dst = Path(dst_path).resolve()
    input_dir = dst / "Input"

    ngen_bin = input_dir / "ngen"
    if not ngen_bin.exists():
        msg = f"ngen binary not found at: {ngen_bin}"
        LOG.critical(msg)
        raise FileNotFoundError(msg)

    realization_files = list(dst.rglob("*realization*.json"))
    if not realization_files:
        msg = f"No realization file found in destination run folder: {input_dir}"
        LOG.critical(msg)
        raise FileNotFoundError(msg)
    realization_file = str(realization_files[0])

    part_files = list(input_dir.rglob("*partition*.json"))
    part_file = str(part_files[0]) if part_files else None

    if part_file:
        with open(part_file) as f:
            partitions = json.load(f)
        nprocs = len(partitions.get("partitions", []))
    else:
        nprocs = 1

    # Read realization file and retrieve checkpoint save path and frequency
    with open(realization_file) as f:
        real_config = json.load(f)
    state_saving = real_config.get("state_saving", [])
    save_config = next((s for s in state_saving if s.get("direction") == "save"), None)
    if save_config is None:
        LOG.info("No state saving configuration found in realization file")

    rb = RealizationBuilder.__new__(RealizationBuilder)
    rb.realization_file = realization_file
    rb.part_file = part_file
    rb.work_dir = str(dst)
    rb.valid_yaml = None
    rb.run_type = "checkpoint"
    rb.basin = infer_gage_id(src_path)
    rb.input_configs = {"Parallel": {"nprocs": nprocs}}
    rb.checkpoint_interval = save_config.get("frequency")
    rb.save_checkpoint_to = save_config.get("path")
    return rb


def run_restart(rb: RealizationBuilder) -> None:
    """
    Run the provided checkpoint restart realization.
    """

    LOG.info("Running restart realization")
    ngen_runner = NgenRunnerAsync(rb=rb, postprocess=False)
    ngen_runner.start()
    ngen_runner.stream_status_until_complete()
    ngen_runner.close()


def _main(src_path: str, dst_path: str) -> None:

    checkpoint_restart(
        src_path=src_path,
        dst_path=dst_path,
    )

    rb = infer_rb(dst_path, src_path)
    cfg = RTEAsyncConfig(
        nprocs=rb.input_configs["Parallel"]["nprocs"],
    )
    cfg.configure_ngen_log(rb)
    LOG.info(f"Starting restart run from: {dst_path}")
    run_restart(rb)


def main(src_path: str, dst_path: str) -> None:
    _rte_transmit_job_start()
    try:
        _main(src_path, dst_path)
    except Exception as e:
        transmit(exc=e)
        _rte_transmit_job_failed()
        raise e
    else:
        _rte_transmit_job_complete()


def cli_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restart a default ngen realization from a checkpoint.",
        formatter_class=cli_args.HelpFormatter,
    )
    parser.add_argument("--src_path", "-src", required=True, help="Path to the existing run to restart from.")
    parser.add_argument("--dst_path", "-dst", required=True, help="Path to the new restart run destination. Defaults to src_path + '_restart'.")
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    main(
        src_path=args.src_path,
        dst_path=args.dst_path,
    )
