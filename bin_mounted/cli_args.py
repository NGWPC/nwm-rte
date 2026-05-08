import argparse
import sys
from dataclasses import dataclass
from enum import StrEnum

import consts as c
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT

# from mswm.utils.settings import c.LAGGED_ENSEMBLE_MEMBER_LAGS
# TODO replace with import of mswm.utils.settings.c.LAGGED_ENSEMBLE_MEMBER_LAGS
from utils import (
    datetime_type,
    timedelta_from_effective_days,
    timedelta_from_pandas_str,
)


class Script(StrEnum):
    DEFAULT = "run_default"
    CALIBRATION = "run_calibration"
    FORECAST = "run_forecast"
    TESTS = "run_tests"
    ALL = "all"


@dataclass
class ArgsKwargs:
    """Simple args list and kwargs dict to be passed later to parser.add_argument(*args, **kwargs).
    The scripts attr is used to indicate which scripts this argument should be added to. See add_args_for_script()."""

    args: list
    kwargs: dict
    # Scripts that use this arg
    scripts: list[Script]


class HelpFormatter(
    argparse.RawTextHelpFormatter,
    argparse.ArgumentDefaultsHelpFormatter,
):
    """Custom help formatter"""

    def _format_action(self, action):
        r"""Add \n between each argument."""
        return super()._format_action(action) + "\n"

    def _format_action_invocation(self, action):
        """Remove metavar and add [boolean switch] for args that are boolean flags."""
        if action.option_strings:
            flags = ", ".join(action.option_strings)
            if isinstance(action, argparse._StoreTrueAction):
                flags = f"{flags} [boolean switch]"
            # Add default value to flags line
            if action.default is not argparse.SUPPRESS and action.default is not None:
                flags = f"{flags} (default: {action.default})"
            return flags
        return ""

    def _get_help_string(self, action):
        """Return raw help without default appended (default being added to top line in other method)"""
        return action.help or ""


def split_iter_to_chunked_str(
    iterable,
    element_separator: str = ", ",
    chunk_size: int = 3,
    chunk_separator: str = "\n    ",
    prepend_chunk_separator: bool = True,
) -> str:
    """Split the provided iterable into chunks of the provided size and
    return str casts of the elements, with parameters for controlling the details."""
    result = chunk_separator.join(
        element_separator.join(map(repr, map(str, iterable[i : i + chunk_size])))
        for i in range(0, len(iterable), chunk_size)
    )
    if prepend_chunk_separator:
        result = chunk_separator + result
    return result


def add_args_for_script(parser: argparse.ArgumentParser, script: Script) -> None:
    current_module = sys.modules[__name__]
    for symbol_name in dir(current_module):
        item = getattr(current_module, symbol_name)
        if type(item) is ArgsKwargs:
            if script in item.scripts or Script.ALL in item.scripts:
                add_arg(parser, item)


def add_arg(parser: argparse.ArgumentParser, arg: ArgsKwargs) -> None:
    """Helper function to add a CLI argument to an existing argparse parser."""
    parser.add_argument(*arg.args, **arg.kwargs)


DEL_SCRATCH = ArgsKwargs(
    args=["-delscratch", "--delete_scratch_and_mesh_first"],
    kwargs={
        "action": "store_true",
        "help": """Delete scratch dir and ESMF mesh files before the run,
which forces ESMF and NetCDF actions to occur.""",
    },
    scripts=[Script.ALL],
)

DEL_RAW = ArgsKwargs(
    args=["-delraw", "--delete_forcing_raw_input_first"],
    kwargs={
        "action": "store_true",
        "help": f"""Delete contents of {repr(c.DIR_FORCING_RAW_INPUT)} before the run,
which forces forcing data to be re-downloaded.""",
    },
    scripts=[Script.ALL],
)

DURATION = ArgsKwargs(
    args=["-dur", "--duration"],
    kwargs={
        "type": timedelta_from_effective_days,
        "default": c.CALIB_SIM_DURATION_DEFAULT,
        "help": """Duration of calibration or default realization. Units: days (integer).""",
    },
    scripts=[Script.CALIBRATION, Script.DEFAULT],
)

FCST_RUN_NAME = ArgsKwargs(
    args=["-rname", "--fcst_run_name"],
    kwargs={
        "type": str,
        "default": c.DEFAULT_FORECAST_RUN_NAME,
        "help": "Forecast run name.",
    },
    scripts=[Script.FORECAST, Script.DEFAULT, Script.TESTS],
)

GAGE_ID = ArgsKwargs(
    args=["-g", "--gage_id"],
    kwargs={
        "type": str,
        "default": c.DEFAULT_GAGE_ID,
        "help": "Gage ID.",
    },
    scripts=[Script.ALL],
)

CYCLE_DATETIME = ArgsKwargs(
    args=["-dt", "--cycle_datetime"],
    kwargs={
        "type": datetime_type,
        "required": True,
        "help": f"""For a regular forecast, this is the start time.
When cold-start is used, this is the *end* of the cold-start cycle.
Format: {repr(DEFAULT_DATETIME_FORMAT.replace("%", "%%"))}.""",
    },
    scripts=[Script.FORECAST, Script.DEFAULT],
)

GLOBAL_DOMAIN = ArgsKwargs(
    args=["-gdomain", "--global_domain"],
    kwargs={
        "type": str,
        "default": c.GLOBAL_DOMAINS[0],
        "choices": c.GLOBAL_DOMAINS,
        "help": "Global domain/region of forcing data.",
    },
    scripts=[Script.ALL],
)

LAGGED_ENSEMBLE = ArgsKwargs(
    args=["-le", "--lagged-ensemble"],
    kwargs={
        "dest": "lagged_ensemble_args",
        "type": str,
        "nargs": 3,
        "required": False,
        "help": f"""Provide this multi-part argument to run one member
of a lagged ensemble (see nwm-fcst-mgr function `run_lagged_ensemble`).
Only applicable to the "medium_range" forcing configuration.
Not applicable to the cold-start realization.

To run an ensemble, call this script multiple times
with varying values for this argument, e.g. "mem1", "mem2", etc.

This argument has 3 parts:
    1. member_name : str (required when -le provided)
        Name of the ensemble member. Choose from: {split_iter_to_chunked_str(list(c.LAGGED_ENSEMBLE_MEMBER_LAGS))}
    2. open_loop_state : str (optional)
        Path to an existing open-loop state file.
        To omit, provide an empty string for this part.
    3. closed_loop_state : str (optional)
        Path to an existing closed-loop state file.
        To omit, provide an empty string for this part.

To run a lagged ensemble member without the optional parts,
provide them as empty strings e.g. `-le 'mem2' '' ''`.""",
    },
    scripts=[Script.FORECAST, Script.DEFAULT],
)

MODELS_CSV = ArgsKwargs(
    args=["-mf", "--model-formulation"],
    kwargs={
        "dest": "model_formulation_cli_csv",
        "type": str,
        "required": False,
        "default": c.DEFAULT_MODEL_FORMULATION_ARGS[0],
        "help": """Provide this argument to specify a non-default model formulation.
The value should be a comma-separated string of models that make up the formulation.
Can be used in conjunction with ["-rz", "--root-zone"].""",
    },
    scripts=[Script.DEFAULT, Script.CALIBRATION],
)

MODELS_RZ = ArgsKwargs(
    args=["-rz", "--root-zone"],
    kwargs={
        "dest": "model_formulation_cli_rootzone",
        "type": str,
        "required": False,
        "default": c.DEFAULT_MODEL_FORMULATION_ARGS[1],
        "help": """Provided value is converted to Boolean and passed as `cfe_aet_rootzone`.
The value should be either true/yes/1 or false/no/0.
Can be used in conjunction with ["-mf", "--model-formulation"].""",
    },
    scripts=[Script.DEFAULT, Script.CALIBRATION],
)

TIMESTAMP_RUN_NAME_SUFFIX = ArgsKwargs(
    args=["-ts", "--timestamp_run_name"],
    kwargs={
        "dest": "add_timestamp_to_run_name",
        "action": "store_true",
        "help": "If provided, add a timestamp suffix to the run name.",
    },
    scripts=[Script.FORECAST, Script.DEFAULT],
)

NWM_OUTPUT_VARIABLES = ArgsKwargs(
    args=["-nwmout", "--nwm_output_vars_true"],
    kwargs={
        "dest": "nwm_output_vars",
        "action": "store_true",
        "help": "If provided, NWMOutputConfig.nwm_output_variables will be set to True",
    },
    scripts=[Script.FORECAST, Script.DEFAULT],
)

FORCING_CONFIGURATION = ArgsKwargs(
    args=["-fconfig", "--forcing_configuration"],
    kwargs={
        "type": str,
        "help": f"""Forcing configuration to use, e.g., 'short_range', 'standard_ana', 'aorc', etc.
Choices and defaults vary per realization type:
  Forecast Realization:
    Default: {repr(c.FORECAST_FORCING_TYPES[0])}. Choices:{split_iter_to_chunked_str(c.FORECAST_FORCING_TYPES)}
  Calibration Realization:
    Default: {repr(c.CALIB_FORCING_TYPES[0])}. Choices: {split_iter_to_chunked_str(c.CALIB_FORCING_TYPES)}
  Default Realization:
    Default: {repr(c.CALIB_FORCING_TYPES[0])}. Choices: {split_iter_to_chunked_str(c.ALL_FORCING_TYPES)}""",
    },
    scripts=[Script.FORECAST, Script.DEFAULT, Script.CALIBRATION],
)

N_PROCS = ArgsKwargs(
    args=["-n", "--nprocs"],
    kwargs={
        "type": int,
        "help": "Number of processors",
        "default": c.DEFAULT_NPROCS,
    },
    scripts=[Script.ALL],
)

OBJECTIVE_FUNCTION = ArgsKwargs(
    args=["-ofunc", "--objective_function"],
    kwargs={
        "type": c.CalObjective,
        "help": """Objective function of previously-ran calibration realization
for basis of forecast. Affects directory path.""",
        "default": c.CALIB_OBJECTIVE_FUNCTION,
    },
    scripts=[Script.CALIBRATION, Script.FORECAST],
)

OPTIMIZATION_ALGORITHM = ArgsKwargs(
    args=["-optalgo", "--optimization_algorithm"],
    kwargs={
        "type": c.CalOptimizationAlgo,
        "help": """Optimization algorithm of previously-ran calibration realization
for basis of forecast. Affects directory path.""",
        "default": c.CALIB_OPTIMIZATION_ALGO,
    },
    scripts=[Script.CALIBRATION, Script.FORECAST],
)

FORCING_STATIC_DIR = ArgsKwargs(
    args=["-fstatic", "--forcing_static_dir"],
    kwargs={
        "type": str,
        "default": c.FORCING_STATIC_DIR_DEFAULT,
        "help": "Directory for static forcing files, used when forcing_provider is 'bmi'.",
    },
    scripts=[Script.ALL],
)

HYDROFAB_FILE = ArgsKwargs(
    args=["--hydrofab_file"],
    kwargs={
        "type": str,
        "default": None,
        "help": "Path to local hydrofabric gpkg file. If provided, bypasses msw-mgr Icefabric API call.",
    },
    scripts=[Script.ALL],
)

WORKER_NAME = ArgsKwargs(
    args=["--wrkr", "--worker_name"],
    kwargs={
        "type": str,
        "help": """If provided, will be used as the worker name,
instead of letting cal mgr choose a random worker name.
Only allowed for Optimization Algorithm DDS, which uses
single instances of ngen. Does not affect 'default'
realization (which is not a calibration).""",
    },
    scripts=[Script.CALIBRATION],
)

CALIB_EVAL_DELAYMENT = ArgsKwargs(
    args=["-evaldelay", "--calib_eval_delayment"],
    kwargs={
        "type": timedelta_from_pandas_str,
        "default": c.CALIB_EVAL_DELAYMENT_DEFAULT,
        "help": """Used to calculate the start time of the calibration evaluation.
Format: pandas-style timedelta string.
See class CalibTimeWindows for details.""",
    },
    scripts=[Script.CALIBRATION],
)

CALIB_VALID_ADVANCE = ArgsKwargs(
    args=["-validadvance", "--valid_sim_advancement"],
    kwargs={
        "type": timedelta_from_pandas_str,
        "default": c.VALID_SIM_ADVANCEMENT_DEFAULT,
        "help": """
Used to calculate the start time of the validation simulation.
Format: pandas-style timedelta string.
See class CalibTimeWindows for details.""",
    },
    scripts=[Script.CALIBRATION],
)

CALIB_EVAL_CURTAILMENT = ArgsKwargs(
    args=["-evalcurtail", "--valid_eval_curtailment"],
    kwargs={
        "type": timedelta_from_pandas_str,
        "default": c.VALID_EVAL_CURTAILMENT_DEFAULT,
        "help": """Used to calculate the end of the validation evaluation.
Format: pandas-style timedelta string.
See class CalibTimeWindows for details.""",
    },
    scripts=[Script.CALIBRATION],
)

COLD_START_DATETIME = ArgsKwargs(
    args=["-csdt", "--cold_start_datetime"],
    kwargs={
        "type": datetime_type,
        "help": """If provided, a cold-start realization will be ran prior to the forecast,
and this value will be the start time for the cold-start.
Format: {DEFAULT_DATETIME_FORMAT}.""",
    },
    scripts=[Script.FORECAST],
)
