"""Misc utilities and type handlers"""

import os
from datetime import datetime, timedelta
from datetime import timezone

import pandas as pd

from mswm.build_inputs import RealizationBuilder
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT as DDF


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
        assert not "." in effective_days  # not a float
        effective_days = int(effective_days)
    else:
        raise TypeError(type(efective_days))
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
