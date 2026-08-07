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
import hashlib
import os
import tempfile
from datetime import datetime, timedelta

import yaml

from ngen_rte import consts as c
from ngen_rte.utils import datetime_type

from NextGen_Forcings_Engine_BMI.run_bmi_model import run_bmi
# The vendored engine's own model.py uses this nested copy of the regrid
# module, not its top-level sibling.
from NextGen_Forcings_Engine_BMI.NextGen_Forcings_Engine.core import regrid as _regrid_nested

print = functools.partial(print, flush=True)


def _make_stable_weight_file_names(stable_geogrid_path: str):
    """For coastal runs, to reuse precomputed weights between simulations,
    make the filename consistent between simulations (product_name +
    geogrid only, no per-process random component)."""

    def _get_weight_file_names(mpi_config, config_options, input_forcings):
        if not config_options.weightsDir:
            return None, None
        file_key = f"{input_forcings.product_name}_{stable_geogrid_path}"
        hash_key = hashlib.md5(file_key.encode()).hexdigest()[:8]
        weight_file = os.path.join(
            config_options.weightsDir, f"ESMF_weight_{hash_key}.nc4"
        )
        if config_options.grid_type == "unstructured":
            weight_file_elem = os.path.join(
                config_options.weightsDir, f"ESMF_weight_{hash_key}_elem.nc4"
            )
        else:
            weight_file_elem = None
        return weight_file, weight_file_elem

    return _get_weight_file_names


def build_config(forcing_configuration: str, global_domain: str, b_date_proc: datetime | None = None) -> tuple[str, dict]:
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
    if b_date_proc is not None:
        cfg["RefcstBDateProc"] = b_date_proc.strftime("%Y%m%d%H%M")

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
    # Read template once upfront to determine AnAFlag and forecast horizons,
    # so we can compute b_date_proc before calling build_config().
    template_path = os.path.join(c.FORCING_TEMPLATE_DIR, f"{forcing_configuration}_config.yml")
    with open(template_path) as f:
        raw_cfg = yaml.safe_load(f)
    ana_flag = raw_cfg.get("AnAFlag", 0)

    if start_time is not None and end_time is not None:
        b_date_proc = start_time
    elif cycle_datetime is not None:
        forecast_hours = forecast_hours_from_config(raw_cfg)
        start_time = cycle_datetime + timedelta(hours=1)
        end_time = cycle_datetime + timedelta(hours=forecast_hours)
        # b_date_proc is always the raw cycle_datetime, ana_flag or not --
        # matching every other script in this codebase (run_default.py,
        # run_forecast.py, run_regionalization_standalone.py all pass
        # cycle_datetime straight through via configs.py's shared
        # mswm_ForcingConfig property, with no compensating offset). This
        # used to pre-add (LookBack - OutputFrequency) minutes for
        # ana_flag runs, on the theory that config.py's
        # calculate_lookback_window() would subtract the same amount back
        # off and land on cycle_datetime again -- confirmed live (and by
        # tracing calculate_lookback_window's actual arithmetic) that this
        # was backwards: it shifted the whole processing window (LookBack
        # - OutputFrequency) minutes into the FUTURE from cycle_datetime
        # instead of producing the intended backward-looking AnA window
        # ending AT cycle_datetime. Passing cycle_datetime unmodified lets
        # calculate_lookback_window's own subtraction do what it's meant
        # to: b_date_proc(final) = cycle_datetime - (LookBack -
        # OutputFrequency), e_date_proc = cycle_datetime.
        b_date_proc = cycle_datetime
    else:
        raise ValueError("Must provide either --cycle_datetime or both --start_time and --end_time")

    config_path, cfg = build_config(forcing_configuration, global_domain, b_date_proc=b_date_proc)

    geogrid = f"{c.COASTAL_GEOGRID_DIR}/geo_em_{global_domain}.nc"

    # Must be applied before run_bmi() below.
    _regrid_nested.get_weight_file_names = _make_stable_weight_file_names(geogrid)

    output_dir = os.path.join(
        c.FORCING_ROOT_DIR, "scratch", f"{forcing_configuration}_coastal"
    )
    os.makedirs(output_dir, exist_ok=True)
    # Must match COASTAL_CONFIG_OVERRIDES["RegridWeightsDir"] in consts.py --
    # under esmf_mesh/ so it lands in a host-mounted, persistent directory
    # instead of being wiped when the container exits.
    os.makedirs(os.path.join(c.FORCING_ROOT_DIR, "esmf_mesh", "regrid_weights"), exist_ok=True)
    file_date = cycle_datetime if cycle_datetime is not None else b_date_proc
    output_path = os.path.join(output_dir, f"{global_domain}_{file_date.strftime('%Y%m%d%H%M')}.nc")

    print("Running coastal forcing engine:")
    print(f"  fcst_run_name         : {fcst_run_name}")
    print(f"  forcing_configuration : {forcing_configuration}")
    print(f"  global_domain         : {global_domain}")
    print(f"  cycle_datetime        : {cycle_datetime}")
    print(f"  start_time            : {start_time}")
    print(f"  end_time              : {end_time}")
    print(f"  ana_flag              : {ana_flag}")
    print(f"  RefcstBDateProc       : {b_date_proc.strftime('%Y%m%d%H%M')}")
    print(f"  config                : {config_path}")
    print(f"  geogrid               : {geogrid}")
    print(f"  output                : {output_path}")

    run_bmi(
        start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
        end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
        config_path=config_path,
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
