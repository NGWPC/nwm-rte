"""Paths and domain names used by coastal forcing generation."""

from pathlib import Path

from ngen_rte import consts as rte_consts

DEFAULT_RUN_NAME = "coastal_run1"
DEBUG_CONUS_SUBSET = "CONUS_debug_gauge_01123000"
SPATIAL_META_SUFFIX = {
    "CONUS": "CONUS",
    "Alaska": "AK",
    "Hawaii": "HI",
    "Puerto_Rico": "PRVI",
}
GEOGRID_DIR = Path(rte_consts.FORCING_ROOT_DIR) / "esmf_mesh" / "NWM" / "domain"
REGRID_WEIGHTS_DIR = Path(rte_consts.FORCING_ROOT_DIR) / "esmf_mesh" / "regrid_weights"
