"""Misc utilities and type handlers"""

import consts as c
import os
from datetime import datetime, timedelta
from datetime import timezone
import json
import pathlib
import shutil

import pandas as pd

from mswm.build_inputs import RealizationBuilder
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT as DDF
from mswm.utils import settings as mswm_settings


def datetime_type(datetime_str) -> datetime:
    """Helper function for munging CLI string arguments into datetime type."""
    return datetime.strptime(datetime_str, mswm_settings.DEFAULT_DATETIME_FORMAT)


def configure_ngen_log(fallback_log_dir: str | pathlib.Path, description: str) -> None:
    """Configure the ngen logging, by
    setting the associated OS env variable for the directory to hold the logs, and
    copying the associated json file into that directory.
    Parameters:
        fallback_log_dir : str
            Is ignored when the RTE OS env var key NGEN_LOG_TO_RTE is true.
            Used to emulate behavior of nwm-cal-mgr and nwm-fcst-mgr (what they would use without RTE)
        description : str
            Is ignored when the RTE OS env var key NGEN_LOG_TO_RTE is false.
            Used to build the timestamped dir name.
    """
    fallback_log_dir = str(fallback_log_dir)  # In case it arrived as a pathlib.Path
    now_str = datetime.now(timezone.utc).strftime(r"%Y%m%d_%H%M%S_%f")
    # Confirm that it's valid json content
    print(f"Reading: {c.SRC_LOG_CONFIG_JSON}")
    with open(c.SRC_LOG_CONFIG_JSON) as f:
        try:
            _ = json.load(f)
        except Exception as e:
            raise RuntimeError(
                f"Could not read or parse as json: {c.SRC_LOG_CONFIG_JSON}: {e}"
            ) from e

    # Decide the dir
    setting_val = os.environ.get(c.RTE_NGEN_LOG_BEHAVIOR_KEY, "").lower().strip()
    if setting_val == "true":
        log_dir = os.path.join("/ngen-app/rte_ngen_logs", f"{now_str}_{description}")
    elif setting_val == "false":
        log_dir = fallback_log_dir
    else:
        raise ValueError(
            f"Invalid value for key {repr(c.RTE_NGEN_LOG_BEHAVIOR_KEY)}: {repr(setting_val)}"
        )

    # Make the dir, copy the log json config into it, and set the OS env var for ngen to be able to find it.
    print(f"Making directory: {log_dir}")
    os.makedirs(log_dir, exist_ok=True)
    print(f"Copying: {c.SRC_LOG_CONFIG_JSON} -> {log_dir}/")
    shutil.copy2(c.SRC_LOG_CONFIG_JSON, log_dir)
    print(f"Setting OS env var {c.NGEN_LOG_DIR_KEY} to {log_dir}")
    os.environ[c.NGEN_LOG_DIR_KEY] = log_dir


def datetime_from_str(datetime_str: str) -> datetime:
    """Convert string to datetime object"""
    return datetime.strptime(datetime_str, DDF)


def str_from_datetime(dt: datetime) -> str:
    """Convert datetime object to string"""
    return dt.strftime(DDF)


def timedelta_from_effective_days(effective_days: int | str) -> timedelta:
    """Build and return a timedelta object from an integer that represents days."""
    if isinstance(effective_days, int):
        pass
    elif isinstance(effective_days, str):
        assert "." not in effective_days  # not a float
        effective_days = int(effective_days)
    else:
        raise TypeError(type(effective_days))
    hours_raw = effective_days * 24
    return timedelta(hours=hours_raw - 1)


def effective_days_from_timedelta(td: timedelta) -> int:
    """Convert a timedelta object to an integer representing effective days."""
    assert isinstance(td, timedelta)
    seconds = td.total_seconds()
    hours = seconds / (60 * 60)

    rem = hours % 24
    if (
        rem != 23
    ):  # timedelta should technically be one hour less than a full day, to account for the final timestep.
        raise ValueError(f"Expected rem to be 23, got {rem}")

    effective_hours = hours + 1
    assert effective_hours % 24 == 0
    effective_days = effective_hours / 24.0
    assert round(effective_days) == effective_days
    return round(effective_days)


def timedelta_from_pandas_str(td_str: str | timedelta) -> timedelta:
    """Convert a pandas-style time string to a timedelta object.
    E.g. '2 days' or '30 min'."""
    return pd.to_timedelta(td_str).to_pytimedelta()


def get_calibration_log_file_overwrite_path(rb: RealizationBuilder) -> str:
    """Build and return a path to use as an overwrite to the calibration log file path."""
    current_time = datetime.now(timezone.utc).strftime(r"%Y%m%d_%H%M%S")
    calib_log_path_overwrite = os.path.join(
        rb.work_dir, "logs", f"calibration_{current_time}.log"
    )
    return calib_log_path_overwrite
