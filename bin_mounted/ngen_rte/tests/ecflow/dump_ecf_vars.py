"""Simulate a reaction to RTE running a forecast as an ecFlow Subtask,
fetching, parsing, and dumping the ecFlow metadata about the RTE Subtask.
Dump ecFlow metadata about the Subtask's status and info variables to JSON files on disk.

Usage:
    See ``run_test_ecf_task_mgr.sh``
"""

import argparse
import json
from pathlib import Path

from ecf_task_mgr import (
    EcflowConnection,
    EcflowInterface,
    ECFVariableSuffix,
    SubtaskCallbackContext,
)

_SETTINGS_FILE = (
    Path(__file__).parent.parent.parent / "run_config" / "ecflow_settings.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ecf-task",
        required=True,
        help="Full ecFlow task path, e.g. /nwm/hourly/nwm_analysis_assim/jnwm_conus_analysis_assim",
    )
    parser.add_argument(
        "--ecf-subtask",
        required=True,
        help="Subtask variable base name, e.g. no_subtask_type__20260615_120000_000000__gage__01123000",
    )
    parser.add_argument(
        "--outdir", required=True, help="Directory to write output JSON files"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to ecFlow server using settings: {_SETTINGS_FILE}")
    conn = EcflowConnection(settings_path=Path(_SETTINGS_FILE))
    iface = EcflowInterface(conn)

    ctx = SubtaskCallbackContext(
        task_path=args.ecf_task,
        subtask_var_base=args.ecf_subtask,
    )

    print(f"Task path : {ctx.task}")
    print(f"Status var: {ctx.var_status}")
    print(f"Info var  : {ctx.var_info}")

    # Status variable
    to_dump = None
    if iface.var_exists(ctx.task, ctx.var_status):
        raw_status = iface.var_fetch(ctx.task, ctx.var_status)
        to_dump = {
            "variable": ctx.var_status,
            "value": raw_status,
            "missing": False,
        }
    else:
        print(f"WARNING: status variable '{ctx.var_status}' not found on server.")
        to_dump = {"variable": ctx.var_status, "value": None, "missing": True}

    status_file = outdir / f"{args.ecf_subtask}{ECFVariableSuffix.STATUS}.json"
    status_file.write_text(json.dumps(to_dump, indent=2))
    print(f"Wrote: {status_file}")

    # Info variable
    to_dump = None
    if iface.var_exists(ctx.task, ctx.var_info):
        raw_info = iface.var_fetch(ctx.task, ctx.var_info).strip()
        try:
            parsed_info = json.loads(raw_info) if raw_info else []
        except json.JSONDecodeError:
            print(
                f"WARNING: info variable '{ctx.var_info}' contains non-JSON value: {repr(raw_info)}"
            )
            parsed_info = raw_info
        to_dump = {
            "variable": ctx.var_info,
            "value": parsed_info,
            "missing": False,
        }
    else:
        print(f"WARNING: info variable '{ctx.var_info}' not found on server.")
        to_dump = {"variable": ctx.var_info, "value": None, "missing": True}

    info_file = outdir / f"{args.ecf_subtask}{ECFVariableSuffix.INFO}.json"
    info_file.write_text(json.dumps(to_dump, indent=2))
    print(f"Wrote: {info_file}")


if __name__ == "__main__":
    main()
