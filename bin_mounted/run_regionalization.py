"""RTE regionalization workflow runner script."""

import argparse
import functools
import logging
import os
import subprocess

print = functools.partial(print, flush=True)

EVAL_VERF_PYTHON_BINARY = "/ngen-app/venvs/eval_verf/bin/python"

REG_REPO_ROOT = "/ngen-app/nwm-region-mgr"
REG_CONFIGS = f"{REG_REPO_ROOT}/configs"
VERF_DATA = "/ngen-app/nwm-verf/data"

# Create a logger for RTE
logger = logging.getLogger("RTE")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def run_cmd(cmd: list[str], check: bool = True, cwd: str = None, shell: bool = False):
    if shell:
        cmd = " ".join(cmd)

    msg = f"Running regionalization command: {' '.join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)}"
    logger.info(msg)

    subprocess.run(cmd, check=check, cwd=cwd, shell=shell)


def main(config_dir: str, parreg: bool, formreg: bool, ngen: bool, run_eval: bool):
    if parreg:
        run_cmd(
            cmd=[
                "python -um nwm_region_mgr",
                config_dir,
                "parreg",
            ],
            shell=True,
        )

    if formreg:
        run_cmd(
            cmd=[
                "python -um nwm_region_mgr",
                config_dir,
                "formreg",
            ],
            shell=True,
        )

    if ngen:
        run_cmd(
            cmd=[
                "python -um nwm_region_mgr",
                config_dir,
                "ngen",
            ],
            shell=True,
        )

    if run_eval:
        run_cmd(
            cmd=[
                EVAL_VERF_PYTHON_BINARY,
                "-um",
                "nwm.verf",
                f"{config_dir}/config_eval.yaml",
            ],
            shell=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_dir", type=str, default=REG_CONFIGS)
    parser.add_argument("--parreg", action="store_true")
    parser.add_argument("--formreg", action="store_true")
    parser.add_argument("--ngen", action="store_true")
    # eval is a python keyword so dest should be something else
    parser.add_argument("--eval", dest="run_eval", action="store_true")
    args = parser.parse_args()
    # print(f"{__file__}: args: {args}")

    assert os.path.exists(REG_REPO_ROOT)
    assert os.path.exists(args.config_dir)
    assert os.path.exists(VERF_DATA)

    main(**vars(args))
