import argparse
from dataclasses import dataclass

# from mswm.utils.settings import LAGGED_ENSEMBLE_MEMBER_LAGS
# TODO replace with import of mswm.utils.settings.LAGGED_ENSEMBLE_MEMBER_LAGS
from consts import LAGGED_ENSEMBLE_MEMBER_LAGS, DEFAULT_MODEL_FORMULATION_ARGS


@dataclass
class ArgsKwargs:
    """Simple args list and kwargs dict to be passed later to parser.add_argument(*args, **kwargs)"""

    args: list
    kwargs: dict


def add_arg(parser: argparse.ArgumentParser, arg: ArgsKwargs) -> None:
    """Helper function to add a CLI argument to an existing argparse parser."""
    parser.add_argument(*arg.args, **arg.kwargs)


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
)

TIMESTAMP_RUN_NAME_SUFFIX = ArgsKwargs(
    args=["-ts", "--timestamp_run_name"],
    kwargs={
        "dest": "add_timestamp_to_run_name",
        "action": "store_true",
        "help": "If provided, add a timestamp suffix to the run name.",
    },
)

NWM_OUTPUT_VARIABLES = ArgsKwargs(
    args=["-nwmout", "--nwm_output_vars_true"],
    kwargs={
        "dest": "nwm_output_vars",
        "action": "store_true",
        "help": "If provided, NWMOutputConfig.nwm_output_variables will be set to True",
    },
)
