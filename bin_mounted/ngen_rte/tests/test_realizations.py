"""Tests for building and running ngen realizations. Called by pytest."""

import logging
import os

from mswm.build_inputs import RealizationBuilder

from ngen_rte import configs, run_default
from ngen_rte import consts as c
from ngen_rte.utils import build_realization


def test_run_default_realization():
    logging.info("Starting default realization test")
    rb, cfg = _build_default_realization()
    ngen_runner = run_default.run_default(rb, cfg)
    output_ngen_stdout_stderr_log = (
        ngen_runner.fem.ngen_proc_stdout_stderr_log_file_path
    )

    logging.info(f"Reading: {output_ngen_stdout_stderr_log}")
    with open(output_ngen_stdout_stderr_log) as f:
        log_content = f.read()
        log_lines = log_content.splitlines()

    for i, line in enumerate(log_lines):
        logging.info(
            f"Line {i} of {repr(os.path.basename(output_ngen_stdout_stderr_log))}: {line}"
        )

    critical_lines = [x for x in log_lines if "CRITICAL" in x]
    fatal_lines = [x for x in log_lines if "FATAL" in x]

    if critical_lines or fatal_lines:
        msg = f"{len(critical_lines)} critical lines and {len(fatal_lines)} fatal lines found in: {repr(output_ngen_stdout_stderr_log)}"
        logging.critical(f"critical lines: {critical_lines}")
        logging.critical(f"fatal lines: {fatal_lines}")
        raise RuntimeError(msg)


def _build_default_config() -> configs.RTEDefaultConfig:
    parser = run_default.cli_arg_parser()
    args = parser.parse_args(
        [
            "--forcing_configuration",
            "aorc",
            "--cycle_datetime",
            "2013-07-25 00:00:00",
            "--duration",
            "2",
            "--fcst_run_name",
            "test_default_aorc",
            "--nprocs",
            "2",
            "--gage_id",
            c.DEFAULT_GAGE_ID,
            "--hydrofab_file",
            c.TEST_HYDROFAB_FILE,
        ]
    )
    cfg = configs.RTEDefaultConfig(**vars(args))
    return cfg


def _build_default_realization() -> tuple[configs.RTEDefaultConfig, RealizationBuilder]:
    cfg = _build_default_config()
    rb = build_realization(
        cfg.mswm_RealizationBuilder_kwargs, "build_default_realization"
    )
    return rb, cfg
