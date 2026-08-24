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
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

import yaml

from ngen_rte import consts as c
from ngen_rte.utils import datetime_type

from NextGen_Forcings_Engine_BMI.run_bmi_model import BMIMODEL, parse_config, run_bmi
# Two separate regrid dispatch paths in the vendored engine, each resolving
# to a different copy of this (byte-identical) module: InputForcings goes
# through consts.py's REGRID_MAP, which hardcodes an absolute import of the
# nested copy; SuppPcp goes through suppPrecipMod.py's own relative import,
# which resolves to the top-level copy (since the model is driven through
# the top-level bmi_model.py). Both need patching.
from NextGen_Forcings_Engine_BMI.NextGen_Forcings_Engine.core import regrid as _regrid_nested
from NextGen_Forcings_Engine.core import regrid as _regrid_toplevel

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


def _destroy_esmf_objects(product_obj) -> None:
    """Explicitly release native ESMF memory (Grid/Field/Regrid) held by one
    product's InputForcings/SuppPrecip object.

    ESMPy's Grid/Field/Regrid classes register their own __del__ as an atexit
    hook, but that only fires once the object is fully unreferenced -- which
    never happens here, since the forcing engine caches these on its
    input_forcing_mod/supp_pcp_mod dicts for the run's whole lifetime. Must
    be called explicitly once we're done needing a product's regrid state.
    """
    for attr in (
        "regridObj", "regridObj_elem",
        "esmf_field_in", "esmf_field_in_elem",
        "esmf_field_out", "esmf_field_out_elem",
        "esmf_grid_in", "esmf_grid_in_elem",
    ):
        obj = getattr(product_obj, attr, None)
        if obj is not None:
            obj.destroy()
            setattr(product_obj, attr, None)


def _slice_parallel_lists(cfg: dict, list_field: str, keep_indices: list[int], name_filter) -> None:
    """In-place: for every top-level cfg list matching list_field's original
    length and satisfying name_filter, keep only entries at keep_indices.

    NextGen_Forcings_Engine configs use parallel arrays (one entry per
    configured product) across ~20 fields -- this keeps them all in sync
    without hardcoding every field name.
    """
    original_len = len(cfg[list_field])
    for field, value in list(cfg.items()):
        if isinstance(value, list) and len(value) == original_len and name_filter(field):
            cfg[field] = [value[i] for i in keep_indices]


def _trim_config_to_single_product(cfg: dict, kind: str, key: int) -> dict:
    """Return a copy of cfg reduced to a single InputForcings or SuppPcp
    product (keeping that product's parallel-array fields in sync), so
    warming its regrid weights doesn't also build ESMF state for every
    other configured product in the same process."""
    cfg = dict(cfg)
    is_supp = lambda field: "Supp" in field

    if kind == "input":
        idx = cfg["InputForcings"].index(key)
        _slice_parallel_lists(cfg, "InputForcings", [idx], lambda f: not is_supp(f))
        _slice_parallel_lists(cfg, "SuppPcp", [], is_supp)
    else:
        # SuppPcp requires at least one InputForcings entry -- config.py
        # rejects an empty list -- so keep the first one as a placeholder.
        # warm_weights() processes InputForcings products first, so its
        # weight file is already cached: a cheap disk load, not a second
        # full weight computation.
        _slice_parallel_lists(cfg, "InputForcings", [0], lambda f: not is_supp(f))
        idx = cfg["SuppPcp"].index(key)
        _slice_parallel_lists(cfg, "SuppPcp", [idx], is_supp)

    return cfg


def build_config(
    forcing_configuration: str,
    global_domain: str,
    b_date_proc: datetime | None = None,
    single_product: tuple[str, int] | None = None,
    lookback: int | None = None,
    forecast_input_horizons: int | None = None,
) -> tuple[str, dict]:
    """Load an existing forecast config template, patch coastal overrides,
    substitute placeholders, and return the path to a temporary config file
    and the raw config dict. If single_product is given, trim the config
    down to just that one InputForcings/SuppPcp product (see
    _trim_config_to_single_product).

    lookback/forecast_input_horizons: CLI-level overrides for the template's
    own LookBack/ForecastInputHorizons (minutes) -- AnA-only, see caller
    (main()) for the AnAFlag guard. Move together: b_date_proc (the window's
    real start) comes from LookBack, but the number of samples actually
    written comes from ForecastInputHorizons -- see forecast_hours_from_config()
    and main()'s own comment on why the two are independent."""
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

    # Known domains (CONUS/Alaska/Hawaii/Puerto_Rico) use an abbreviated
    # GEOGRID_LDASOUT_Spatial_Metadata_<suffix>.nc filename; any other
    # (e.g. custom-extracted) domain name is expected to match its own
    # geo_em_<global_domain>.nc / GEOGRID_LDASOUT_Spatial_Metadata_<global_domain>.nc
    # pair directly, with no separate abbreviation.
    spatial_meta_suffix = c.COASTAL_SPATIAL_META_SUFFIX.get(global_domain, global_domain)

    overrides = {
        k: v.replace("{spatial_meta_suffix}", spatial_meta_suffix) if isinstance(v, str) else v
        for k, v in c.COASTAL_CONFIG_OVERRIDES.items()
    }
    cfg.update(overrides)
    cfg["ScratchDir"] = f"{{root_dir}}/scratch/{forcing_configuration}_coastal/"
    if b_date_proc is not None:
        cfg["RefcstBDateProc"] = b_date_proc.strftime("%Y%m%d%H%M")
    if lookback is not None:
        cfg["LookBack"] = lookback
    if forecast_input_horizons is not None:
        cfg["ForecastInputHorizons"] = [forecast_input_horizons] * len(cfg.get("ForecastInputHorizons", [1]))

    if single_product is not None:
        cfg = _trim_config_to_single_product(cfg, *single_product)

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


def run_single_product_warmup(
    forcing_configuration: str,
    global_domain: str,
    cycle_datetime: datetime,
    kind: str,
    key: int,
) -> None:
    """Warm one product's regrid weight cache, then explicitly release its
    ESMF state before this process exits.

    Called by warm_weights() in its own subprocess per product, so peak
    memory here never exceeds a single product's footprint -- process exit
    alone would already reclaim everything, but we destroy explicitly first
    anyway (see _destroy_esmf_objects) since that's also what a normal,
    multi-product run needs and doesn't do.
    """
    config_path, _ = build_config(
        forcing_configuration, global_domain, b_date_proc=cycle_datetime, single_product=(kind, key)
    )
    geogrid = f"{c.COASTAL_GEOGRID_DIR}/geo_em_{global_domain}.nc"
    _stable_weight_file_names = _make_stable_weight_file_names(geogrid)
    _regrid_nested.get_weight_file_names = _stable_weight_file_names
    _regrid_toplevel.get_weight_file_names = _stable_weight_file_names
    os.makedirs(os.path.join(c.FORCING_ROOT_DIR, "esmf_mesh", "regrid_weights"), exist_ok=True)

    # Diagnostic: force verbose ESMF-level logging (PET<N>.ESMF_LogFile) by
    # creating the Manager singleton ourselves before the vendored code's own
    # implicit ESMF.Manager() call -- Manager.__init__ is a no-op on any call
    # after the first, so this makes debug logging apply globally for this
    # process. chdir first so the log files land somewhere persistent
    # (bind-mounted), not the container's ephemeral writable-tmpfs overlay.
    import esmpy as _ESMF_debug
    esmf_log_dir = os.path.join(c.FORCING_ROOT_DIR, "scratch", f"{forcing_configuration}_coastal", "esmf_debug_logs")
    os.makedirs(esmf_log_dir, exist_ok=True)
    os.chdir(esmf_log_dir)
    _ESMF_debug.Manager(debug=True)
    print(f"ESMF debug logging enabled, logs in: {esmf_log_dir}")

    print(f"Warming weights for {kind} product {key} (config={config_path})")

    with open(config_path) as fp:
        parsed = parse_config(yaml.safe_load(fp))
    model = BMIMODEL[parsed.get("GRID_TYPE")]()
    model.initialize_with_params(config_path, b_date=None, geogrid=geogrid, output_path=None)
    model.update()

    for product_dict in (model._input_forcing_mod, model._supp_pcp_mod):
        for product_obj in (product_dict or {}).values():
            _destroy_esmf_objects(product_obj)

    model.finalize()
    print(f"Weights warmed for {kind} product {key}")


def warm_weights(forcing_configuration: str, global_domain: str, cycle_datetime: datetime) -> None:
    """Precompute and cache ESMF regrid weight files for every product
    configured in forcing_configuration, one product per subprocess.

    A single process holding all configured products' ESMF grids/fields/
    weight matrices simultaneously is what OOM'd on the last CONUS attempt.
    One subprocess per product bounds peak memory to a single product's
    weight matrix instead of the sum of every configured product.
    """
    template_path = os.path.join(c.FORCING_TEMPLATE_DIR, f"{forcing_configuration}_config.yml")
    with open(template_path) as f:
        raw_cfg = yaml.safe_load(f)

    # InputForcings first: a SuppPcp-only warmup needs an already-cached
    # InputForcings weight file as its placeholder (config.py rejects an
    # empty InputForcings list).
    jobs = [("input", key) for key in raw_cfg.get("InputForcings", [])]
    jobs += [("supp", key) for key in raw_cfg.get("SuppPcp", [])]

    for kind, key in jobs:
        print(f"--- Warming {kind} product {key} in a fresh subprocess ---")
        result = subprocess.run([
            sys.executable, "-um", "ngen_rte.run_coastal",
            "-dt", cycle_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "-fconfig", forcing_configuration,
            "-gdomain", global_domain,
            "--warm_single_product", f"{kind}:{key}",
        ])
        if result.returncode != 0:
            raise RuntimeError(f"Weight warming failed for {kind} product {key} (exit code {result.returncode})")

    print(f"Weight warming complete for all products in '{forcing_configuration}'.")


def main(
    fcst_run_name: str,
    forcing_configuration: str,
    global_domain: str,
    cycle_datetime: datetime | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    lookback: int | None = None,
    forecast_input_horizons: int | None = None,
) -> None:
    # Read template once upfront to determine AnAFlag and forecast horizons,
    # so we can compute b_date_proc before calling build_config().
    template_path = os.path.join(c.FORCING_TEMPLATE_DIR, f"{forcing_configuration}_config.yml")
    with open(template_path) as f:
        raw_cfg = yaml.safe_load(f)
    ana_flag = raw_cfg.get("AnAFlag", 0)

    if (lookback is not None or forecast_input_horizons is not None) and ana_flag != 1:
        raise ValueError(
            "-lb/--lookback and -fih/--forecast_input_horizons are AnA-only overrides "
            f"(they patch the AnA-specific lookback-window mechanics) -- '{forcing_configuration}' "
            f"has AnAFlag={ana_flag}, not 1."
        )
    if forecast_input_horizons is not None:
        # Must land in raw_cfg (not just the copy build_config() re-loads and
        # patches later) since forecast_hours_from_config() below reads
        # raw_cfg directly to compute end_time -- build_config()'s own patch
        # only affects the temp YAML the forcing engine itself consumes.
        raw_cfg["ForecastInputHorizons"] = [forecast_input_horizons] * len(raw_cfg.get("ForecastInputHorizons", [1]))

    if start_time is not None and end_time is not None:
        b_date_proc = start_time
    elif cycle_datetime is not None:
        forecast_hours = forecast_hours_from_config(raw_cfg)
        if ana_flag == 1:
            # AnA: start_time/end_time here only control ITERATION COUNT
            # (a plain count(date_range(start_time, end_time)) computation
            # inside the engine) -- the actual per-sample output timestamps
            # come from calculate_lookback_window()'s own b_date_proc-based
            # computation, entirely decoupled from these two values. Keep
            # the +1h here as-is -- confirmed live (LookBack=240/
            # ForecastInputHorizons=240 -> exactly 4 correct T-3..T0 AnA
            # samples); changing it would add/remove an iteration and
            # desync the sample count from what's actually being requested.
            start_time = cycle_datetime + timedelta(hours=1)
        else:
            # SR (ana_flag=0, LookBack=-9999 in the template):
            # calculate_lookback_window() never fires for this branch, so
            # start_time here directly IS the first real output timestamp,
            # not just an iteration-count input. The previous +1h made
            # ngen_forcing_sr skip a genuine T0 sample entirely -- start
            # exactly at cycle_datetime instead so SR's own T0 boundary
            # sample actually exists (schism_sr/sfincs_sr need to start at
            # T0 with real T0 forcing, not a synthetic +1h-shifted start --
            # see gen_configs_sr.ecf).
            start_time = cycle_datetime
        end_time = cycle_datetime + timedelta(hours=forecast_hours)
        # calculate_lookback_window() handles the AnA lookback internally.
        b_date_proc = cycle_datetime
    else:
        raise ValueError("Must provide either --cycle_datetime or both --start_time and --end_time")

    config_path, cfg = build_config(
        forcing_configuration, global_domain, b_date_proc=b_date_proc,
        lookback=lookback, forecast_input_horizons=forecast_input_horizons,
    )

    geogrid = f"{c.COASTAL_GEOGRID_DIR}/geo_em_{global_domain}.nc"

    # Must be applied before run_bmi() below.
    _stable_weight_file_names = _make_stable_weight_file_names(geogrid)
    _regrid_nested.get_weight_file_names = _stable_weight_file_names
    _regrid_toplevel.get_weight_file_names = _stable_weight_file_names

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
        help=(
            f"Output domain. Default: {repr(c.COASTAL_GLOBAL_DOMAINS[0])}. "
            f"Not restricted to {c.COASTAL_GLOBAL_DOMAINS} -- any domain name "
            "with a matching geo_em_<name>.nc / "
            "GEOGRID_LDASOUT_Spatial_Metadata_<name>.nc pair under "
            f"{c.COASTAL_GEOGRID_DIR} works (e.g. one produced by "
            "forecast_demo/bin/extract_esmf_domain.py)."
        ),
    )
    parser.add_argument(
        "-lb", "--lookback",
        type=int,
        default=None,
        help=(
            "AnA-only: override the config template's own LookBack (minutes). "
            "Errors if the template's AnAFlag != 1. Move together with "
            "--forecast_input_horizons -- LookBack sets the window's real "
            "start, but the number of samples written comes from "
            "ForecastInputHorizons independently."
        ),
    )
    parser.add_argument(
        "-fih", "--forecast_input_horizons",
        type=int,
        default=None,
        help=(
            "AnA-only: override the config template's own ForecastInputHorizons "
            "(minutes) uniformly across all configured products. Errors if the "
            "template's AnAFlag != 1."
        ),
    )
    parser.add_argument(
        "--warm_weights",
        action="store_true",
        help="Precompute regrid weight files for every product in the config, one product per subprocess, instead of running a simulation. Requires --cycle_datetime.",
    )
    parser.add_argument(
        "--warm_single_product",
        type=str,
        default=None,
        help=argparse.SUPPRESS,  # internal: used by warm_weights()'s own subprocess re-invocation, format "kind:key"
    )
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()

    if args.warm_single_product is not None:
        kind, key_str = args.warm_single_product.split(":")
        run_single_product_warmup(
            forcing_configuration=args.forcing_configuration,
            global_domain=args.global_domain,
            cycle_datetime=args.cycle_datetime,
            kind=kind,
            key=int(key_str),
        )
    elif args.warm_weights:
        if args.cycle_datetime is None:
            parser.error("--warm_weights requires --cycle_datetime")
        warm_weights(
            forcing_configuration=args.forcing_configuration,
            global_domain=args.global_domain,
            cycle_datetime=args.cycle_datetime,
        )
    else:
        if args.cycle_datetime is None and not (args.start_time and args.end_time):
            parser.error("Provide either --cycle_datetime or both --start_time and --end_time")
        main(
            cycle_datetime=args.cycle_datetime,
            start_time=args.start_time,
            end_time=args.end_time,
            fcst_run_name=args.fcst_run_name,
            forcing_configuration=args.forcing_configuration,
            global_domain=args.global_domain,
            lookback=args.lookback,
            forecast_input_horizons=args.forecast_input_horizons,
        )
