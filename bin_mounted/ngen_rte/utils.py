"""Misc utilities and type handlers"""

import json
import os
import re
import traceback
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ecflow
import pandas as pd
from ecf_task_mgr import EcflowInterface, SubtaskCallbackContext, SubtaskInfoVarEntry
from ewts import LogParts, Status
from ewts import Payload as Pld
from ewts.modules import ModuleKey
from mswm.build_inputs import RealizationBuilder
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT
from pydantic import ConfigDict, validate_call

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
    ecf_iface: EcflowInterface | None = None,
    ecf_ctx: SubtaskCallbackContext | None = None,
) -> None:
    """Transmit information about the run.

    Args:
        log_parts: The structured log message to transmit.
        log_file: Path to the log file (basename will be extracted).
        exc: An exception instance, if an error occurred.
        The following must be provided together:
            ecf_iface: Optional EcflowInterface for sending status to ecFlow server.
            ecf_ctx: Optional SubtaskCallbackContext for ecFlow server reporting

    For concerns:
        If the payload itself has an error status, consider that FATAL.

        If exc is not None, consider that FATAL.

        Otherwise, mirror the severity of the log message rather than the payload,
        e.g. send a CRITICAL message through LOG.critical().

    If ecf_iface and ecf_ctx are provided:
        Status payloads will be reported to the ecFlow server.
        Concern-level messages will be reported to the ecFlow server.
    """
    if (ecf_iface is not None and ecf_ctx is None) or (
        ecf_iface is None and ecf_ctx is not None
    ):
        raise ValueError(
            "Both ecf_iface and ecf_ctx must be provided together, or neither."
        )

    log_file_bn = Path(log_file).name if log_file else None
    exc_info = ExcInfo(exc) if exc is not None else None

    tx_dict = {
        "concern": False,
        "log_parts": None,
        "payload": None,
        "log_file": None,
        "exc_info": None,
    }

    # Default to transmitting as INFO, override with other level depending on circumstances.
    transmitter = getattr(LOG, "info")

    if log_parts:
        tx_dict["log_parts"] = asdict(log_parts, dict_factory=dict_factory)

        if log_parts.level in TRANSMISSION_CONCERN_LOG_LEVELS:
            # Mimic the level of the original log message
            tx_dict["concern"] = True
            transmitter = getattr(LOG, log_parts.level.lower())

        if log_parts.payload:
            tx_dict["payload"] = asdict(log_parts.payload, dict_factory=dict_factory)
            if log_parts.payload.status == Status.ERROR:
                tx_dict["concern"] = True
                transmitter = LOG.fatal

            # Report status payloads to ecFlow server if interface provided
            if ecf_ctx:
                entry = SubtaskInfoVarEntry(
                    status=ecflow.State.active,
                    data=asdict(log_parts.payload, dict_factory=dict_factory),
                )
                ecf_iface.subtask_var_info_append(ecf_ctx, entry)

    if exc_info:
        tx_dict["concern"] = True
        tx_dict["exc_info"] = asdict(exc_info)
        transmitter = LOG.fatal

        # Report exception/concern to ecFlow server if interface provided
        if ecf_ctx:
            entry = SubtaskInfoVarEntry(
                status=ecflow.State.aborted,
                data=asdict(exc_info),
            )
            ecf_iface.subtask_var_info_append(ecf_ctx, entry)

    if log_file:
        tx_dict["log_file"] = log_file_bn

    transmitter(f"tx: {tx_dict}")


@validate_call(config=ConfigDict(strict=True))
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
            # Transmit the checkpoint settings explicitly so ecFlow can detect
            _rte_transmit_checkpoint_settings(rb)
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


def _rte_transmit_job_start(ecf_iface=None, ecf_ctx=None):
    """General transmission for job starting"""
    transmit(
        LogParts_payload_only(
            Pld(Status.STARTING, msg="Starting job", modnm=MODULE_KEY.value)
        )
    )
    if ecf_iface:
        ecf_iface.subtask_var_info_append(
            ecf_ctx,
            entry=SubtaskInfoVarEntry(
                status=ecflow.State.active,
                data={"msg": "RTE job starting"},
            ),
        )
        ecf_iface.subtask_var_status_set(ecf_ctx, ecflow.State.active)


def _rte_transmit_job_complete(
    ecf_iface=None,
    ecf_ctx=None,
    rb: RealizationBuilder = None,
    log_paths_meta: dict | None = None,
    exc: None = None,
):
    """General transmission for job completion"""
    transmit(
        LogParts_payload_only(
            Pld(Status.COMPLETE, msg="Job complete", modnm=MODULE_KEY.value)
        )
    )
    if ecf_iface:
        ecf_iface.subtask_var_info_append(
            ecf_ctx,
            entry=SubtaskInfoVarEntry(
                status=ecflow.State.complete,
                data={"msg": "RTE job complete"}
                | get_saved_state_info(rb)
                | log_paths_meta,
            ),
        )
        ecf_iface.subtask_var_status_set(ecf_ctx, ecflow.State.complete)
    if exc is not None:
        raise RuntimeError(f"Unexpected non-None exc provided: {exc}")


def _rte_transmit_job_failed(
    ecf_iface=None,
    ecf_ctx=None,
    rb: RealizationBuilder | None = None,
    log_paths_meta: dict | None = None,
    exc: Exception | None = None,
):
    """General transmission for job failure.
    Information is always sent to the RTE log.
    If the ecFlow objects are provided, then information is sent to the ecFlow server:
        If ``rb`` is provided, then information about the saved checkpoints / saved states is sent to the ecFlow server.
        If ``exc`` is provided, then the "reason" (ecFlow term) of the abort is built as the exception message and the formatted traceback.
            Else, the "reason" is a generic string indicating that the reason was not set.
    """
    transmit(
        LogParts_payload_only(
            Pld(Status.ERROR, msg="Job failed", modnm=MODULE_KEY.value)
        )
    )
    if ecf_iface:
        if exc:
            reason = f"{exc}: {''.join(traceback.TracebackException.from_exception(exc).format())}"
        else:
            reason = "reason-not-set"
        ecf_iface.subtask_var_info_append(
            ecf_ctx,
            entry=SubtaskInfoVarEntry(
                status=ecflow.State.aborted,
                reason=reason,
                data={"msg": "RTE job failed"}
                | get_saved_state_info(rb)
                | log_paths_meta,
            ),
        )
        ecf_iface.subtask_var_status_set(ecf_ctx, ecflow.State.aborted)


def _rte_transmit_checkpoint_settings(rb: RealizationBuilder) -> None:
    """Transmit the checkpoint settings from the provided RealizationBuilder instance."""
    checkpoint_settings = {
        "checkpoint_interval": getattr(rb, "checkpoint_interval", None),
        "save_checkpoint_to": getattr(rb, "save_checkpoint_to", None),
    }
    dumped = json.dumps(checkpoint_settings, default=str)
    status = Status.NULL
    msg = f"checkpoint_settings={dumped}"
    modnm = ModuleKey.MSW_MGR.value
    transmit(LogParts_payload_only(Pld(status, msg=msg, modnm=modnm)))


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


def os_walk__get_stats(path: str) -> tuple[int, int, str]:
    """Walk the provided directory recursively and calculate/determine:
    Total file count.
    Total size of files in bytes.
    Relative path of newest file."""
    file_count = 0
    size_bytes = 0
    newest_relpath = None
    newest_mtime = 0
    for root, dirs, files in os.walk(path):
        file_count += len(files)
        size_bytes += sum(os.path.getsize(os.path.join(root, f)) for f in files)
        for fn in files:
            fp = os.path.join(root, fn)
            mtime = os.path.getmtime(fp)
            if mtime > newest_mtime:
                newest_mtime = mtime
                newest_relpath = os.path.relpath(fp, start=path)
    return file_count, size_bytes, newest_relpath


def get_saved_state_info(rb: RealizationBuilder | None) -> dict:
    """Get paths for ``save_checkpoint_to`` and ``save_state_to`` from the provided RealizationBuilder instance,
    and list those directories to get metadata about them. Save the information into a dict and return the dict.
    The intended use for this is for building a SubtaskInfoVarEntry instance to transmit to ecFlow server.

    Pathlib forms are converted to string before being returned, to support serialization.
    """
    parent_d = {"states": {}}

    d = parent_d["states"]
    for key in ("save_checkpoint_to", "save_state_to"):
        d[key] = None
        d[f"{key}_stats"] = None
        path = getattr(rb, key, None)
        if path:
            path = str(path)
            file_count, size_bytes, newest_relpath = os_walk__get_stats(path)
            d[key] = path
            d[f"{key}_stats"] = {
                "file_count": file_count,
                "size_bytes": size_bytes,
                "newest_relpath": newest_relpath,
            }

    return parent_d
