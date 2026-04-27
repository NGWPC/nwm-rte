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
    status_obs_build: TestStat
    status_obs_run: TestStat
    build_exc: str | None
    exe_exc: str | None


def parse_raw_result(raw_result: dict) -> ParsedResult:
    parsed_result = ParsedResult(
        models_csv=raw_result["rb_kwargs"]["config_overrides"]["General"]["models"],
        use_rootzone=bool(
            raw_result["rb_kwargs"]["config_overrides"]["ModuleProperties"][
                "cfe_aet_rootzone"
            ]
        ),
        status_obs_build=TestStat(raw_result["rb_stat"]),
        status_obs_run=TestStat(raw_result["fcst_exe_stat"]),
        build_exc=raw_result["rb_excep_msg"],
        exe_exc=raw_result["fcst_exe_excep_msg"],
    )
    return parsed_result


def is_match(pr: dict, row: pd.Series) -> bool:
    """Return True if the parsed result dict (from json)
    is an effective match with the row object (from tsv file). Else return False."""
    if (
        row["formulation_mswm"] == pr.models_csv
        and row["uses_root_zone"] == pr.use_rootzone
    ):
        return True
    return False


def main(model_formulations_file: str | None = None) -> None:
    """See module docstring for general behavior. See CLI help for CLI behavior."""

    print(f"Reading: {c.TEST_RESULTS_FILE}")
    with open(c.TEST_RESULTS_FILE) as f:
        raw_results = json.load(f)

    parsed_results: list[ParsedResult] = [parse_raw_result(rr) for rr in raw_results]
    print(f"Parsed {len(parsed_results)} results")

    if model_formulations_file is None:
        return

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
        parse_errors = []

        assert isinstance(row["uses_root_zone"], bool)
        matches = [pr for pr in parsed_results if is_match(pr, row)]

        if len(matches) != 1:
            parse_errors.append(
                f"{len(matches)} matches in {os.path.basename(c.TEST_RESULTS_FILE)}"
            )

        # Write to dataframe. When there are multiple matches in the results
        # for a particular row in the table, that is okay as long as there is
        # agreement among the matches.
        for key in ("status_obs_build", "status_obs_run", "build_exc", "exe_exc"):
            assert key in df_mff.columns
            choices = [str(getattr(m, key)) for m in matches]
            if len(set(choices)) == 1:
                df_mff.at[i, key] = choices[0]
            else:
                df_mff.at[i, key] = "CONFLICT"
                parse_errors.append(f"Conflict for {repr(key)}: {'vs '.join(choices)}")

        df_mff.at[i, "parse_errors"] = ", ".join(parse_errors)

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
