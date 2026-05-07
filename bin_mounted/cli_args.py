import argparse
import sys
from dataclasses import dataclass
from enum import StrEnum

import consts as c

# from mswm.utils.settings import LAGGED_ENSEMBLE_MEMBER_LAGS
# TODO replace with import of mswm.utils.settings.LAGGED_ENSEMBLE_MEMBER_LAGS
from consts import DEFAULT_MODEL_FORMULATION_ARGS, LAGGED_ENSEMBLE_MEMBER_LAGS


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
        "help": "Delete scratch dir and ESMF mesh files before the run, which forces ESMF and NetCDF actions to occur.",
    },
    scripts=[Script.ALL],
)


DEL_RAW = ArgsKwargs(
    args=["-delraw", "--delete_forcing_raw_input_first"],
    kwargs={
        "action": "store_true",
        "help": f"Delete contents of {repr(c.DIR_FORCING_RAW_INPUT)} before the run, which forces forcing data to be re-downloaded.",
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
        "help": f"""Provide this multi-part argument to run one member of a lagged ensemble (see nwm-fcst-mgr function `run_lagged_ensemble`).
        Only applicable to the "medium_range" forcing configuration.
        Not applicable to the cold-start realization.

        To run an ensemble, call this script multiple times with varying values for this argument, e.g. for "mem1", "mem2", etc.

        This argument has 3 parts:
            1. member_name : str (required when -le provided)
                Name of the ensemble member. Choose from: {list(LAGGED_ENSEMBLE_MEMBER_LAGS)}
            2. open_loop_state : str (optional)
                Path to an existing open-loop state file.
                To omit, provide an empty string for this part.
            3. closed_loop_state : str (optional)
                Path to an existing closed-loop state file.
                To omit, provide an empty string for this part.
        
        To run a lagged ensemble member without the optional parts, provide them as empty strings e.g. `-le 'mem2' '' ''`.
        """,
    },
    scripts=[Script.FORECAST, Script.DEFAULT],
)

MODELS_CSV = ArgsKwargs(
    args=["-mf", "--model-formulation"],
    kwargs={
        "dest": "model_formulation_cli_csv",
        "type": str,
        "required": False,
        "help": f"""Provide this argument to specify a non-default model formulation.
        The value should be a comma-separated string of models that make up the formulation.
        Can be used in conjunction with ["-rz", "--root-zone"].
        Default: {DEFAULT_MODEL_FORMULATION_ARGS[0]}.""",
    },
    scripts=[Script.DEFAULT, Script.CALIBRATION],
)

MODELS_RZ = ArgsKwargs(
    args=["-rz", "--root-zone"],
    kwargs={
        "dest": "model_formulation_cli_rootzone",
        "type": str,
        "required": False,
        "help": f"""Provided value is converted to Boolean and passed as `cfe_aet_rootzone`.
        The value should be either true/yes/1 or false/no/0.
        Can be used in conjunction with ["-mf", "--model-formulation"].
        Default: {DEFAULT_MODEL_FORMULATION_ARGS[1]}.""",
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
