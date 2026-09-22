"""Optional ecFlow task manager imports."""

from typing import Any

try:
    import ecflow
    from ecf_task_mgr import (
        EcflowConnection,
        EcflowInterface,
        SubtaskCallbackContext,
        SubtaskInfoVarEntry,
    )
except ImportError:
    ECF_TASK_MGR_AVAILABLE = False
    ecflow = None
    EcflowConnection = Any
    EcflowInterface = Any
    SubtaskCallbackContext = Any
    SubtaskInfoVarEntry = Any
else:
    ECF_TASK_MGR_AVAILABLE = True
