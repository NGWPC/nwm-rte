"""CLI script to generate gridded atmospheric forcing files for coastal models.

NOTE: This includes a T0 output needed for coastal, in addition to the normal T1+ outputs.
NOTE: The T0 output has identical forcing values as T1.
See comments in ngen-forcing model.py function ``write_t0_output``.
An independent T0 state cannot be reliably computed because several forecast products omit required fields at hour zero and substitute hour one. Examples:
https://github.com/NGWPC/ngen-forcing/blob/27e03ba138478dd449ce957b1c3ba4c36fc33d8f/NextGen_Forcings_Engine_BMI/NextGen_Forcings_Engine/core/time_handling.py#L1202-L1206
https://github.com/NGWPC/ngen-forcing/blob/27e03ba138478dd449ce957b1c3ba4c36fc33d8f/NextGen_Forcings_Engine_BMI/NextGen_Forcings_Engine/core/time_handling.py#L1444-L1448
https://github.com/NGWPC/ngen-forcing/blob/27e03ba138478dd449ce957b1c3ba4c36fc33d8f/NextGen_Forcings_Engine_BMI/NextGen_Forcings_Engine/core/time_handling.py#L2043-L2047
https://github.com/NGWPC/ngen-forcing/blob/27e03ba138478dd449ce957b1c3ba4c36fc33d8f/NextGen_Forcings_Engine_BMI/NextGen_Forcings_Engine/core/time_handling.py#L4129-L4135


NOTE:
    See repository ``nwm-coastal`` (file ``nwm-coastal/scripts/setup_data_coastal.sh``) for the scripts needed to download / set up input data required to run coastal forcing workflows:

    These files are masked versions of the full CONUS nc files, masked to an area around the test gage for testing CONUS workflows
    on a machine that may not have enough RAM for an actual full CONUS run:
        run_ngen/data/esmf_mesh/NWM/domain/GEOGRID_LDASOUT_Spatial_Metadata_CONUS_debug_gauge_01123000.nc
        run_ngen/data/esmf_mesh/NWM/domain/geo_em_CONUS_debug_gauge_01123000.nc

Usage:
    Choose exactly one timing mode:

    * ``--cycle_datetime`` (``-dt``) runs an operational forecast cycle. The
        forcing engine determines the time window from the selected configuration.
    * ``--start_time`` (``-start``) together with ``--end_time`` (``-end``) runs
        an explic`it time window, such as an AORC retrospective run.

Examples:
    python -um ngen_rte.coastal.make_coastal_forcing -dt "2025-09-15 00:00:00" -fconfig standard_ana_hawaii -gdomain Hawaii
    python -um ngen_rte.coastal.make_coastal_forcing -start "2013-07-25 00:00:00" -end "2013-07-26 00:00:00" -fconfig aorc -gdomain Hawaii

"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from NextGen_Forcings_Engine_BMI.coastal.gridded.config_manager import (
    CoastalConfigManager,
    analysis_num_updates,
)
from NextGen_Forcings_Engine_BMI.coastal.gridded.warm_regrid_weights import (
    warm_coastal_regrid_weights,
)
from NextGen_Forcings_Engine_BMI.run_bmi_model import run_bmi

from ngen_rte import consts as rte_consts
from ngen_rte.coastal import consts
from ngen_rte.logger import initialize_logger
from ngen_rte.run_config.cli_args import HelpFormatter
from ngen_rte.utils import datetime_type

LOG = initialize_logger()


def make_coastal_forcing(
    forcing_configuration: str,
    global_domain: str,
    run_name: str = consts.DEFAULT_RUN_NAME,
    cycle_datetime: datetime | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    lookback: int | None = None,
    forecast_input_horizons: int | None = None,
    debug_conus_subset: bool = False,
) -> Path:
    """Create one gridded coastal forcing file and return its path."""
    if cycle_datetime is not None and (start_time is not None or end_time is not None):
        raise ValueError("cycle_datetime cannot be combined with start_time/end_time")
    if cycle_datetime is None and (start_time is None or end_time is None):
        raise ValueError("Provide cycle_datetime or both start_time and end_time")
    if (
        lookback is not None or forecast_input_horizons is not None
    ) and cycle_datetime is None:
        raise ValueError("lookback and forecast_input_horizons require cycle_datetime")

    config_manager = CoastalConfigManager(
        forcing_configuration,
        global_domain,
        cycle_datetime=cycle_datetime,
        start_time=start_time,
        lookback=lookback,
        forecast_input_horizons=forecast_input_horizons,
        forcing_root_dir=rte_consts.FORCING_ROOT_DIR,
        forcing_template_dir=rte_consts.FORCING_TEMPLATE_DIR,
        geogrid_dir=consts.GEOGRID_DIR,
        regrid_weights_dir=consts.REGRID_WEIGHTS_DIR,
        spatial_metadata_suffix=consts.SPATIAL_META_SUFFIX,
        debug_subset_name=consts.DEBUG_CONUS_SUBSET,
        debug_conus_subset=debug_conus_subset,
    )
    output_path = config_manager.output_path
    partial_output_path = output_path.with_suffix(f"{output_path.suffix}.partial")
    config_path = config_manager.write_config()
    num_ana_updates = analysis_num_updates(config_path)
    is_ana = num_ana_updates is not None

    LOG.info(
        "Running coastal forcing %s: configuration=%s domain=%s output=%s",
        run_name,
        forcing_configuration,
        global_domain,
        output_path,
    )
    run_arguments = {
        "start_time": (
            start_time.strftime("%Y-%m-%d %H:%M:%S") if start_time else None
        ),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S") if end_time else None,
        "config_path": config_path,
        "cycle_datetime": cycle_datetime,
        "geogrid": str(config_manager.geogrid),
        "output_path": partial_output_path,
        "output_t0": not is_ana,
    }
    if is_ana:
        run_arguments["num_updates"] = num_ana_updates
    run_bmi(**run_arguments)
    partial_output_path.replace(output_path)

    final_msg = f"Coastal forcing written to {output_path}"
    print(final_msg)
    LOG.info(final_msg)
    return output_path


def cli_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=HelpFormatter)
    timing = parser.add_mutually_exclusive_group(required=True)
    timing.add_argument(
        "-dt",
        "--cycle_datetime",
        type=datetime_type,
        help="Operational forecast cycle; cannot be used with --start_time.",
    )
    timing.add_argument(
        "-start",
        "--start_time",
        type=datetime_type,
        help="Start of an explicit time window; requires --end_time.",
    )
    parser.add_argument(
        "-end",
        "--end_time",
        type=datetime_type,
        help="End of an explicit time window; requires --start_time.",
    )
    parser.add_argument(
        "-rname",
        "--fcst_run_name",
        default=consts.DEFAULT_RUN_NAME,
        help=f"Name used in log messages (default: {consts.DEFAULT_RUN_NAME}).",
    )
    parser.add_argument(
        "-fconfig",
        "--forcing_configuration",
        required=True,
        help="Installed forcing template name, such as short_range or aorc.",
    )
    parser.add_argument(
        "-gdomain",
        "--global_domain",
        default="CONUS",
        help="Coastal output domain (default: CONUS).",
    )
    parser.add_argument(
        "-lb",
        "--lookback",
        type=int,
        help=(
            "Analysis-only override for the configured lookback window in minutes. "
            "Requires --cycle_datetime."
        ),
    )
    parser.add_argument(
        "-fih",
        "--forecast_input_horizons",
        type=int,
        help=(
            "Analysis-only uniform override for all configured forecast input "
            "horizons in minutes. Requires --cycle_datetime."
        ),
    )
    parser.add_argument(
        "--warm_weights",
        action="store_true",
        help=(
            "Recreate reusable regrid weights one product per subprocess, replacing "
            "matching cached weights instead of creating a forcing file. Requires "
            "--cycle_datetime."
        ),
    )
    parser.add_argument(
        "--debug_conus_subset",
        action="store_true",
        help=(
            "Use the gauge 01123000 CONUS target-grid subset and isolated output "
            "paths. Requires --global_domain CONUS."
        ),
    )
    return parser


def main() -> None:
    parser = cli_arg_parser()
    args = parser.parse_args()
    if (args.start_time is None) != (args.end_time is None):
        parser.error("--start_time and --end_time must be provided together")
    if args.debug_conus_subset and args.global_domain != "CONUS":
        parser.error("--debug_conus_subset requires --global_domain CONUS")
    if (
        args.lookback is not None or args.forecast_input_horizons is not None
    ) and args.cycle_datetime is None:
        parser.error(
            "--lookback and --forecast_input_horizons require --cycle_datetime"
        )
    if args.warm_weights:
        if args.cycle_datetime is None:
            parser.error("--warm_weights requires --cycle_datetime")
        warm_coastal_regrid_weights(
            forcing_configuration=args.forcing_configuration,
            global_domain=args.global_domain,
            cycle_datetime=args.cycle_datetime,
            lookback=args.lookback,
            forecast_input_horizons=args.forecast_input_horizons,
            forcing_root_dir=rte_consts.FORCING_ROOT_DIR,
            forcing_template_dir=rte_consts.FORCING_TEMPLATE_DIR,
            geogrid_dir=consts.GEOGRID_DIR,
            regrid_weights_dir=consts.REGRID_WEIGHTS_DIR,
            spatial_metadata_suffix=consts.SPATIAL_META_SUFFIX,
            debug_subset_name=consts.DEBUG_CONUS_SUBSET,
            debug_conus_subset=args.debug_conus_subset,
        )
        return

    make_coastal_forcing(
        forcing_configuration=args.forcing_configuration,
        global_domain=args.global_domain,
        run_name=args.fcst_run_name,
        cycle_datetime=args.cycle_datetime,
        start_time=args.start_time,
        end_time=args.end_time,
        lookback=args.lookback,
        forecast_input_horizons=args.forecast_input_horizons,
        debug_conus_subset=args.debug_conus_subset,
    )


if __name__ == "__main__":
    main()
