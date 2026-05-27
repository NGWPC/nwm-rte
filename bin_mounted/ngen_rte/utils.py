"""Misc utilities and type handlers"""

import os
import re
import traceback
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from ewts import LogParts, Status
from ewts import Payload as Pld
from ewts.modules import ModuleKey
from mswm.build_inputs import RealizationBuilder
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

from ngen_rte import consts as c
from ngen_rte.execution.ngen_logs import dict_factory
from ngen_rte.logger import MODULE_KEY, initialize_logger

LOG = initialize_logger()

TRANSMISSION_CONCERN_LOG_LEVELS = (
    "WARNING",
    "ERROR",
    "CRITICAL",
    "SEVERE",
    "FATAL",
)


class MSWMRealizationBuilderInitializeError(Exception):
    """Raised when MSWM fails to initialize an instance of RealizationBuilder"""


class MSWMRealizationBuilderBuildError(Exception):
    """Raised when MSWM fails to build a realization using an instance of RealizationBuilder"""


@dataclass
class ExcInfo:
    """Break up an exception instance into its type, message, traceback object,
    and formatted traceback string (escaped)."""

    e: Exception
    typ: type = field(init=False)
    msg: str = field(init=False)
    tb: str = field(init=False)

    def __post_init__(self):
        self.typ = type(self.e)
        self.msg = str(self.e)
        # Make the traceback string, then escape it.
        tb = "".join(traceback.format_exception(self.e))
        self.tb = tb.replace("\n", "\\n").replace("\t", "\\t")


def transmit(
    log_parts: LogParts = None,
    log_file: Path | str | None = None,
    exc: Exception | None = None,
) -> None:
    """Transmit information about the run.

    TODO Currently this simply calls LOG.info() with the relevant information.
    Actual transmission logic should be implemented (send to file or service).
    """
    log_file_bn = Path(log_file).name if log_file else None
    exc_info = ExcInfo(exc) if exc is not None else None
    if log_parts and log_parts.level in TRANSMISSION_CONCERN_LOG_LEVELS:
        LOG.warning(
            f"Concern: {asdict(log_parts, dict_factory=dict_factory)}. FromLogFile: {log_file_bn}"
        )
    if log_parts.payload:
        LOG.info(
            f"Payload: {asdict(log_parts.payload, dict_factory=dict_factory)}. Exception: {asdict(exc_info) if exc_info else None}. FromLogFile: {log_file_bn}"
        )


def LogParts_payload_only(payload: Pld) -> LogParts:
    """Factory for a LogParts containing only the payload attribute.
    For transmitting structured data that is not associated with a particular log line."""
    kwargs = {f.name: None for f in fields(LogParts)}
    kwargs["payload"] = payload
    kwargs["tolerant"] = True
    return LogParts(**kwargs)


def build_realization(rb_kwargs: dict, build_method: str) -> RealizationBuilder:
    """Build a realization using the provided RealizationBuilder kwargs
    and name of build method. Catch errors and send transmissions."""
    modnm = ModuleKey.MSW_MGR.value
    LOG.info(f"Building realization: {rb_kwargs}")

    e_wrapped = None

    transmit(
        LogParts_payload_only(
            Pld(Status.INITTING, msg="Initializing RealizationBuilder", modnm=modnm)
        )
    )
    try:
        rb = RealizationBuilder(**rb_kwargs)
    except Exception as e:
        msg = f"Failed to initialize RealizationBuilder with kwargs: {rb_kwargs}"
        e_wrapped = MSWMRealizationBuilderInitializeError(msg)
        e_wrapped.__cause__ = e
    else:
        transmit(
            LogParts_payload_only(
                Pld(Status.INITTED, msg="Initialized RealizationBuilder", modnm=modnm)
            )
        )
        transmit(
            LogParts_payload_only(
                Pld(Status.STARTING, msg=f"Calling: {build_method}", modnm=modnm)
            )
        )
        try:
            getattr(rb, build_method)()
        except Exception as e:
            msg = f"Failed to build realization with method {repr(build_method)} from kwargs: {rb_kwargs}"
            e_wrapped = MSWMRealizationBuilderBuildError(msg)
            e_wrapped.__cause__ = e
        else:
            transmit(
                LogParts_payload_only(
                    Pld(Status.COMPLETE, msg=f"Finished: {build_method}", modnm=modnm)
                )
            )

    if e_wrapped is not None:
        transmit(
            LogParts_payload_only(Pld(Status.ERROR, msg=msg, modnm=modnm)),
            exc=e_wrapped,
        )
        raise e_wrapped

    LOG.info(f"Wrote: {rb.realization_file}")
    return rb


def _rte_transmit_job_start():
    """General transmission for job starting"""
    transmit(
        LogParts_payload_only(
            Pld(Status.STARTING, msg="Starting job", modnm=MODULE_KEY.value)
        )
    )


def _rte_transmit_job_complete():
    """General transmission for job completion"""
    transmit(
        LogParts_payload_only(
            Pld(Status.COMPLETE, msg="Job complete", modnm=MODULE_KEY.value)
        )
    )


def make_symlink(link_path: str, target_path: str) -> None:
    """Create a symlink"""
    LOG.info(
        f"Creating symlink, writing {repr(link_path)} to point to {repr(target_path)}"
    )
    if not os.path.exists(target_path):
        raise FileNotFoundError(target_path)
    os.makedirs(os.path.dirname(link_path), exist_ok=True)
    if os.path.exists(link_path):
        LOG.info(f"Deleting existing symlink before recreating it: {link_path}")
        os.remove(link_path)
    os.symlink(target_path, link_path)


def make_wcoss_path_symlinks() -> None:
    """Create symlinks for various WCOSS paths"""
    make_symlink(c.NGEN_BIN__LINK, c.NGEN_BIN__TARGET)
    make_symlink(c.PARTITION_GENERATOR_BIN__LINK, c.PARTITION_GENERATOR_BIN__TARGET)


def datetime_type(datetime_str) -> datetime:
    """Helper function for munging CLI string arguments into datetime type."""
    return datetime.strptime(datetime_str, DEFAULT_DATETIME_FORMAT)


def datetime_from_str(datetime_str: str) -> datetime:
    """Convert string to datetime object"""
    return datetime.strptime(datetime_str, DEFAULT_DATETIME_FORMAT)


def str_from_datetime(dt: datetime) -> str:
    """Convert datetime object to string"""
    return dt.strftime(DEFAULT_DATETIME_FORMAT)


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


def booleanize(booly: str | bool) -> bool:
    """Convert the provided value to a boolean, parsing semantically no/0/false and yes/1/true. Case-insensitive."""
    if isinstance(booly, bool):
        return booly
    elif isinstance(booly, str):
        if booly.lower().strip() in ("no", "0", "false"):
            return False
        elif booly.lower().strip() in ("yes", "1", "true"):
            return True
        else:
            raise ValueError(
                f"Unexpected booly value: {repr(booly)}. Expected no/0/false or yes/1/true (case insensitive)."
            )
    else:
        raise TypeError(f"Unexpected booly type: {type(booly)}")


def parse_fcst_run_name(fcst_run_name: str) -> list[Exception]:
    """Validate the provided forecast run name, and return a list of errors."""
    errors: list[Exception] = []
    if fcst_run_name != fcst_run_name.strip():
        errors.append(
            ValueError(
                f"Whitespace found on end of fcst_run_name: {repr(fcst_run_name)}"
            )
        )
    return errors


def get_paths_for_observed_and_retro_data(
    global_domain: str,
    gage_id: str,
    models_csv: str,
) -> tuple[str | None, str | None, list[Exception]]:
    """Build and return two data paths needed for LSTM model,
    as well as a list of errors encountered during this function.
    Return None for obs_dir and nwmretro_file if not LSTM."""

    errors: list[Exception] = []

    if "lstm" in models_csv.lower():
        obs_dir = find_obs_dir(global_domain, gage_id)
        nwmretro_file = f"{c.NWM_RETRO_STREAMFLOW_DIR}/{gage_id}.csv"
        if not os.path.exists(obs_dir):
            errors.append(NotADirectoryError(obs_dir))
        if not os.path.exists(nwmretro_file):
            errors.append(FileNotFoundError(nwmretro_file))
    else:
        obs_dir = None
        nwmretro_file = None

    return obs_dir, nwmretro_file, errors


def find_obs_dir(global_domain: str, gage_id: str) -> str:
    """Search the grandparent directory of observed flow csv files to determine
    the directory that contains one of them.  Assert that only one such csv file is found.
    If multiple are found, then this function needs to be reworked to handle more complex
    situations, such as multiple vintages of this data existing on disk."""
    grandparent = f"{c.DEFAULT_MAIN_DIR}/data/streamflow_observations/{global_domain}"
    LOG.info(f"Searching directory for observed flow files: {grandparent}")
    candidate_csvs = []
    for root, dirs, files in os.walk(grandparent):
        dirs.sort()
        files.sort()
        for fn in files:
            pattern = f"^{gage_id}_hourly_discharge.csv$"
            if re.fullmatch(pattern, fn):
                candidate_csvs.append(os.path.join(root, fn))
    if len(candidate_csvs) != 1:
        raise ValueError(
            f"Expected to find 1 candidate csv for observed flow for global_domain={global_domain}, gage_id={gage_id}, but found {len(candidate_csvs)} when searching from {repr(grandparent)}: {candidate_csvs}"
        )
    obs_dir = os.path.dirname(candidate_csvs[0])
    return obs_dir
