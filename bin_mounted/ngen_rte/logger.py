"""Logger setup utilities for nwm-rte"""

import os
from datetime import datetime, timezone

import ewts

from ngen_rte import consts as c

LOG = None
MODULE_KEY = ewts.modules.ModuleKey.RTE


def initialize_logger() -> ewts.EwtsLogger:
    """Set up the logger unless it has already been set up. Either way, return it."""
    global LOG
    if LOG is None:
        now_str = datetime.now(timezone.utc).strftime(r"%Y%m%d_%H%M%S_%f")
        log_dir = os.path.join(c.CONTAINER_LOGS_DIR, "rte")
        log_file_name = f"rte_{now_str}.log"
        print(f"RTE: initializing EWTS log at: {os.path.join(log_dir, log_file_name)}")
        ewts_enabled = os.environ.get("EWTS_ENABLED", "").strip().lower() not in ("0", "false", "off", "no")
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
        print(
            f"RTE: done initializing EWTS log at: {os.path.join(log_dir, log_file_name)}"
        )
    return LOG
