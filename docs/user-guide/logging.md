# Logging and Status Transmission

## Log Locations

RTE logs are written to host path `./logs/rte/` (container path `/ngen-app/logs_rte/rte/`). When `NGEN_LOG_TO_RTE` is enabled, ngen logs are consolidated under host path `./logs/ngen/` (container path `/ngen-app/logs_rte/ngen/`); otherwise they remain with the realization output.

## Log Parsing

EWTS is optional and controlled by `RTE_EWTS_ENABLED`. When requested and available, RTE parses log lines into EWTS `LogParts` and extracts structured status `Payload` data. Async default, forecast, and standalone regionalization runs poll ngen MPI logs, ngen stdout/stderr, Model Setup Workflow Manager logs, and Forecast Manager logs, then re-emit relevant messages through the RTE logger.

When EWTS is disabled or unavailable, RTE uses a standard Python logger. Raw lines are still checked for concern keywords such as `WARNING`, `ERROR`, `SEVERE`, and `FATAL`, but structured `LogParts` and status `Payload` parsing is not available.

## ecFlow Client

The optional `ecf_task_mgr` package implements the Python ecFlow client used by RTE. When both `--ecf-task` and `--ecf-subtask` are supplied to `run_default.py`, RTE connects using [`ecflow_settings.json`](../ecflow_settings.json) and reports job state, concerns, checkpoint information, and log metadata to the corresponding ecFlow task. Without those arguments, information remains in the RTE logs and no ecFlow connection is made.

This integration can support deeper scheduler orchestration in future workflows, but it currently reports execution state and metadata for an existing ecFlow task.

## Data-Assimilation Postprocessing

The `run_output_postprocess.py` and `run_output_mosaic.py` wrappers emit RTE job lifecycle messages, but RTE does not consume or retransmit the underlying `nwm-data-assimilation` postprocessing logs. See the `nwm-data-assimilation` and `nextgen-support-scripts` repositories for those workflows.

## See Also

[Diagrams](../diagrams/index.md)
