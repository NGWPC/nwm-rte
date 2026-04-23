"""Read the test results json from a previous run of `run_tests.py` and distill human-readable reporting info"""

import argparse
from dataclasses import dataclass
import functools
import json
import os

import numpy as np
import pandas as pd

from execution_tests import TestStat
import consts as c

print = functools.partial(print, flush=True)


@dataclass
class ParsedResult:
    models_csv: str
    use_rootzone: bool
    build_status: TestStat
    execute_status: TestStat
    build_excep_msg: str | None
    execute_excep_msg: str | None


def parse_raw_result(raw_result: dict) -> ParsedResult:
    parsed_result = ParsedResult(
        models_csv=raw_result["rb_kwargs"]["config_overrides"]["General"]["models"],
        use_rootzone=bool(
            raw_result["rb_kwargs"]["config_overrides"]["ModuleProperties"][
                "cfe_aet_rootzone"
            ]
        ),
        build_status=TestStat(raw_result["rb_stat"]),
        execute_status=TestStat(raw_result["fcst_exe_stat"]),
        build_excep_msg=raw_result["rb_excep_msg"],
        execute_excep_msg=raw_result["fcst_exe_excep_msg"],
    )
    return parsed_result


def main(model_formulations_file: str | None = None) -> None:
    """See module docstring for general behavior. See CLI help for CLI behavior."""

    print(f"Reading: {c.TEST_RESULTS_FILE}")
    with open(c.TEST_RESULTS_FILE) as f:
        raw_results = json.load(f)

    parsed_results: list[ParsedResult] = [parse_raw_result(rr) for rr in raw_results]
    print(f"Parsed {len(parsed_results)} results")

    if model_formulations_file is not None:
        extension = ".tsv"
        print(f"Reading: {model_formulations_file}")
        assert model_formulations_file.endswith(extension)
        df_mff = pd.read_csv(model_formulations_file, sep="\t")

        # Add columns
        for new_col in ["build_exc", "exe_exc", "parse_errors"]:
            if new_col not in df_mff.columns:
                df_mff[new_col] = np.nan

        tgt_file = os.path.splitext(model_formulations_file)[0] + f"_results{extension}"

        for i, row in df_mff.iterrows():
            assert isinstance(row["uses_root_zone"], bool)
            matches = []
            for pr in parsed_results:
                if (
                    row["formulation_mswm"] == pr.models_csv
                    and row["uses_root_zone"] == pr.use_rootzone
                ):
                    matches.append(pr)

            if len(matches) != 1:
                df_mff.at[i, "parse_errors"] = (
                    f"Found {len(matches)} matches in {os.path.basename(c.TEST_RESULTS_FILE)}"
                )
            else:
                match = matches[0]
                df_mff.at[i, "parse_errors"] = None
                df_mff.at[i, "status_obs_build"] = match.build_status.value
                df_mff.at[i, "status_obs_run"] = match.execute_status.value
                df_mff.at[i, "build_exc"] = match.build_excep_msg
                df_mff.at[i, "exe_exc"] = match.execute_excep_msg

        print(f"Writing: {tgt_file}")
        df_mff.to_csv(tgt_file, sep="\t", index=False)


def cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-mff",
        "--model_formulations_file",
        help=f"""If provided, this file should be a tsv of model formulations
        corresponding to the formulations ran in c.TEST_RESULTS_FILE ({c.TEST_RESULTS_FILE}).
        The tsv file will be copied and the results will be added to the copy.
        """,
    )
    return parser


if __name__ == "__main__":
    parser = cli()
    args = parser.parse_args()
    main(**vars(args))
