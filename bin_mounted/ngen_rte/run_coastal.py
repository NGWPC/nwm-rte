"""
Command-line executable to run the NWM forcing engine in gridded output mode
for coastal model forcing. Unlike the standard forecast workflow, this does not
require a gage or catchment — it regrids forcing data to a NWM domain geogrid
and writes netCDF output directly.

Any existing forcing configuration template (e.g. short_range, aorc) can be
used. The script patches in the coastal overrides (GRID_TYPE: gridded,
Output: 1, SpatialMetaIn, GeogridIn) on top of the chosen template.

Timing can be specified either via:
  --cycle_datetime  (operational forecasts: end time derived from ForecastInputHorizons in config template)
  --start_time and --end_time  (explicit time window, e.g. for AORC retrospective)

See `run_coastal.sh` for example calls.
"""

import argparse
import functools
import os
import tempfile
from datetime import datetime, timedelta

import yaml

from ngen_rte import consts as c
from ngen_rte.utils import datetime_type

from NextGen_Forcings_Engine_BMI.run_bmi_model import run_bmi

print = functools.partial(print, flush=True)


def build_config(forcing_configuration: str, global_domain: str) -> tuple[str, dict]:
    """Load an existing forecast config template, patch coastal overrides,
    substitute placeholders, and return the path to a temporary config file
    and the raw config dict."""
    template_path = os.path.join(
        c.FORCING_TEMPLATE_DIR, f"{forcing_configuration}_config.yml"
    )
    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"No config template found for '{forcing_configuration}': {template_path}\n"
            f"Available configs are in {c.FORCING_TEMPLATE_DIR}"
        )

    with open(template_path, "r") as f:
        cfg = yaml.safe_load(f)

    spatial_meta_suffix = c.COASTAL_SPATIAL_META_SUFFIX[global_domain]

    overrides = {
        k: v.replace("{spatial_meta_suffix}", spatial_meta_suffix) if isinstance(v, str) else v
        for k, v in c.COASTAL_CONFIG_OVERRIDES.items()
    }
    cfg.update(overrides)
    cfg["ScratchDir"] = f"{{root_dir}}/scratch/{forcing_configuration}_coastal/"

    content = yaml.dump(cfg, default_flow_style=False)
    content = content.replace("{root_dir}", c.FORCING_ROOT_DIR)
    content = content.replace("{global_domain}", global_domain)

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False)
    tmp.write(content)
    tmp.close()
    return tmp.name, cfg


def forecast_hours_from_config(cfg: dict) -> float:
    """Derive forecast duration in hours from ForecastInputHorizons (minutes) in config."""
    horizons = cfg.get("ForecastInputHorizons", [])
    if not horizons:
        raise ValueError("ForecastInputHorizons not found in config template — cannot derive end_time from --cycle_datetime. Use --start_time and --end_time instead.")
    return max(horizons) / 60.0


def main(
    fcst_run_name: str,
    forcing_configuration: str,
    global_domain: str,
    cycle_datetime: datetime | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> None:
    config_path, cfg = build_config(forcing_configuration, global_domain)

    if start_time is not None and end_time is not None:
        b_date = start_time.strftime("%Y%m%d%H%M")
    elif cycle_datetime is not None:
        forecast_hours = forecast_hours_from_config(cfg)
        start_time = cycle_datetime + timedelta(hours=1)
        end_time = cycle_datetime + timedelta(hours=forecast_hours)
        b_date = start_time.strftime("%Y%m%d%H%M")
    else:
        raise ValueError("Must provide either --cycle_datetime or both --start_time and --end_time")

    geogrid = f"{c.COASTAL_GEOGRID_DIR}/geo_em_{global_domain}.nc"

    output_dir = os.path.join(
        c.FORCING_ROOT_DIR, "scratch", f"{forcing_configuration}_coastal"
    )
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{global_domain}_{b_date}.nc")

    print("Running coastal forcing engine:")
    print(f"  fcst_run_name         : {fcst_run_name}")
    print(f"  forcing_configuration : {forcing_configuration}")
    print(f"  global_domain         : {global_domain}")
    print(f"  cycle_datetime        : {cycle_datetime}")
    print(f"  start_time            : {start_time}")
    print(f"  end_time              : {end_time}")
    print(f"  b_date                : {b_date}")
    print(f"  config                : {config_path}")
    print(f"  geogrid               : {geogrid}")
    print(f"  output                : {output_path}")

    run_bmi(
        start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
        end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
        config_path=config_path,
        b_date=b_date,
        geogrid=geogrid,
        output_path=output_path,
    )

    print(f"Output written to: {output_path}")


def cli_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    timing = parser.add_mutually_exclusive_group()
    timing.add_argument(
        "-dt", "--cycle_datetime",
        type=datetime_type,
        default=None,
        help="Forecast cycle datetime (operational). End time derived from config template. Format: 'YYYY-MM-DD HH:MM:SS'",
    )
    timing.add_argument(
        "-start", "--start_time",
        type=datetime_type,
        default=None,
        help="Explicit simulation start time. Requires --end_time. Format: 'YYYY-MM-DD HH:MM:SS'",
    )
    parser.add_argument(
        "-end", "--end_time",
        type=datetime_type,
        default=None,
        help="Explicit simulation end time. Required when --start_time is used. Format: 'YYYY-MM-DD HH:MM:SS'",
    )
    parser.add_argument(
        "-rname", "--fcst_run_name",
        type=str,
        default=c.DEFAULT_COASTAL_FORECAST_RUN_NAME,
        help=f"Run name. Default: {repr(c.DEFAULT_COASTAL_FORECAST_RUN_NAME)}",
    )
    parser.add_argument(
        "-fconfig", "--forcing_configuration",
        type=str,
        required=True,
        help=(
            "Forcing configuration to use. Must match an existing config template\n"
            f"(without '_config.yml') in {c.FORCING_TEMPLATE_DIR}.\n"
            "Examples: short_range, aorc, short_range_alaska, cold_start_hawaii"
        ),
    )
    parser.add_argument(
        "-gdomain", "--global_domain",
        type=str,
        default=c.COASTAL_GLOBAL_DOMAINS[0],
        choices=c.COASTAL_GLOBAL_DOMAINS,
        help=f"Output domain. Default: {repr(c.COASTAL_GLOBAL_DOMAINS[0])}",
    )
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    if args.cycle_datetime is None and not (args.start_time and args.end_time):
        parser.error("Provide either --cycle_datetime or both --start_time and --end_time")
    main(
        cycle_datetime=args.cycle_datetime,
        start_time=args.start_time,
        end_time=args.end_time,
        fcst_run_name=args.fcst_run_name,
        forcing_configuration=args.forcing_configuration,
        global_domain=args.global_domain,
    )
