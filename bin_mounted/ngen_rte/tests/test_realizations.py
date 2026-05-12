"""Tests for building and running ngen realizations."""

import logging
import os

from mswm.build_inputs import RealizationBuilder
from ngen_rte import configs, run_default
from ngen_rte import consts as c

# def test_build_default_realization():
#     _, _ = _build_default_realization()


def test_run_default_realization():
    rb, cfg = _build_default_realization()
    output_ngen_stdout_stderr_log = run_default.run_default(
        rb, cfg, clear_output_dir=True
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
            "--hydrofab_file",
            c.TEST_HYDROFAB_FILE,
        ]
    )
    cfg = configs.RTEDefaultConfig(**vars(args))
    return cfg


def _build_default_realization() -> tuple[RealizationBuilder, configs.RTEDefaultConfig]:
    cfg = _build_default_config()
    rb = run_default.build_default_realization(cfg)
    return rb, cfg
