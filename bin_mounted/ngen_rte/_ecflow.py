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
    ECFLOW_AVAILABLE = False
    ecflow = None
    EcflowConnection = Any
    EcflowInterface = Any
    SubtaskCallbackContext = Any
    SubtaskInfoVarEntry = Any
else:
    ECFLOW_AVAILABLE = True
