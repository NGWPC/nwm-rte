import argparse
import functools
import os
import subprocess
import sys

from pydantic import validate_call


print = functools.partial(print, flush=True)

# EVAL_VERF_PYTHON_BINARY = "python_eval_verf"
EVAL_VERF_PYTHON_BINARY = "/ngen-app/venvs/eval_verf/bin/python"

REG_REPO_ROOT = "/ngen-app/nwm-region-mgr"
REG_SAMPLE_CONFIGS = f"{REG_REPO_ROOT}/sample_files/configs"


@validate_call
def run_cmd(cmd: list[str], check: bool = True, cwd: str = None, shell: bool = False):
    if shell:
        cmd = " ".join(cmd)
    msg = f"\n\n######## vvvvv\n{__file__}\nshell={shell}\ncwd={cwd}\nrunning={repr(cmd)}\n######## ^^^^^ \n"
    print(msg)
    subprocess.run(cmd, check=check, cwd=cwd, shell=shell)


def main(parreg: bool, formreg: bool, ngen: bool, run_eval: bool):
    if parreg:
        run_cmd(
            cmd=[
                "python",
                f"{REG_REPO_ROOT}/regionalization.py",
                REG_SAMPLE_CONFIGS,
            ],
            cwd=REG_REPO_ROOT,
        )

    if formreg:
        raise NotImplementedError("Not yet tested")
        run_cmd(
            cmd=[
                "python",
                f"{REG_REPO_ROOT}/run_formreg.py",
                f"{REG_SAMPLE_CONFIGS}/config_general.yaml",
                f"{REG_SAMPLE_CONFIGS}/config_formreg.yaml",
            ],
            cwd=REG_REPO_ROOT,
        )

    if ngen:
        cmd = [
            "python",
            f"{REG_REPO_ROOT}/run_ngen_vpu_docker.py",
            "--config_ngen",
            f"{REG_SAMPLE_CONFIGS}/config_ngen.yaml",
        ]
        # TODO remove the ulimit settings after ngen #90 has been merged
        ulimit_extras = ["ulimit", "-n", "60000", "&&"]
        cmd = ulimit_extras + cmd
        run_cmd(
            cmd=cmd,
            cwd=REG_REPO_ROOT,
            shell=True,
        )

    if run_eval:
        raise NotImplementedError("Not yet tested")
        run_cmd(
            cmd=[
                EVAL_VERF_PYTHON_BINARY,
                "-um",
                "nwm.verf",
                f"{REG_SAMPLE_CONFIGS}/config_eval.yaml",
            ],
            cwd=REG_REPO_ROOT,
            shell=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--parreg", action="store_true")
    parser.add_argument("--formreg", action="store_true")
    parser.add_argument("--ngen", action="store_true")
    # eval is a python keyword so dest should be something else
    parser.add_argument("--eval", dest="run_eval", action="store_true")
    args = parser.parse_args()
    print(f"{__file__}: args: {args}")

    assert os.path.exists(REG_REPO_ROOT)
    assert os.path.exists(REG_SAMPLE_CONFIGS)

    main(**vars(args))
