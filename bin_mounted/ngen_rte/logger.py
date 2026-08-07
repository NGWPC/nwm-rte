"""Logger setup utilities for nwm-rte"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import TYPE_CHECKING

from ngen_rte import consts as c


def os_env_var_bool(val: str) -> bool:
    """Convert an OS environment variable string to a Boolean with some semantics."""
    val_munged = val.strip().upper()
    if val_munged in {"YES", "TRUE", "1", "ON"}:
        return True
    elif val_munged in {"NO", "FALSE", "0", "OFF", ""}:
        return False
    else:
        raise ValueError(f"Unexpected value, expected booleanish but got: {val_munged}")


EWTS_REQUESTED = os_env_var_bool(os.environ["RTE_EWTS_ENABLED"])

try:
    if not EWTS_REQUESTED:
        raise ImportError
    import ewts
except ImportError:
    EWTS_AVAILABLE = False
    ModuleKey = SimpleNamespace(
        RTE=SimpleNamespace(value="RTE"),
        MSW_MGR=SimpleNamespace(value="MSW_MGR"),
    )
    MODULE_KEY = ModuleKey.RTE
    Status = SimpleNamespace(
        NULL="NULL",
        INITTING="INITTING",
        INITTED="INITTED",
        STARTING="STARTING",
        COMPLETE="COMPLETE",
        ERROR="ERROR",
    )
else:
    EWTS_AVAILABLE = True
    from ewts import Status as EwtsStatus
    from ewts.modules import ModuleKey

    MODULE_KEY = ModuleKey.RTE
    Status = EwtsStatus

if EWTS_AVAILABLE or TYPE_CHECKING:
    from ewts import EwtsLogger


class FallbackLogger(logging.Logger):
    """Fallback logger used when EWTS is not requested or otherwise unavailable.
    fatal and severe are defined for compatibility with code that expects EWTS methods.
    """

    fatal = logging.Logger.critical
    severe = logging.Logger.error


def _fallback_logger(log_file_path: str) -> FallbackLogger:
    """Fallback logger used when EWTS is not requested or otherwise unavailable."""
    logger = FallbackLogger("ngen_rte")
    handler = logging.FileHandler(log_file_path)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


LOG = None


def initialize_logger() -> EwtsLogger | FallbackLogger:
    """Set up the logger unless it has already been set up. Either way, return it."""
    global LOG
    if LOG is None:
        now_str = datetime.now(timezone.utc).strftime(r"%Y%m%d_%H%M%S_%f")
        log_dir = os.path.join(c.CONTAINER_LOGS_DIR, "rte")
        log_file_name = f"rte_{now_str}.log"
        log_file_path = os.path.join(log_dir, log_file_name)
        if not EWTS_AVAILABLE:
            os.makedirs(log_dir, exist_ok=True)
            LOG = _fallback_logger(log_file_path)
            if EWTS_REQUESTED:
                LOG.warning(
                    "EWTS was requested but is unavailable. Using fallback logging."
                )
            else:
                LOG.warning("EWTS was not requested. Using fallback logging.")
            return LOG

        print(f"RTE: initializing EWTS log at: {log_file_path}")
        LOG = ewts.logger.setup_logger(
            MODULE_KEY,
            level="INFO",
            log_dir=log_dir,
            log_file_name=log_file_name,
            running_in_ngen=False,
            enabled=ewts_enabled,
        )
        if LOG is None:
            raise TypeError("LOG is unexpectedly None after ewts setup_logger call.")
        print(f"RTE: done initializing EWTS log at: {log_file_path}")
    return LOG
