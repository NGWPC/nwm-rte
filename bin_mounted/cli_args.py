from dataclasses import dataclass

# from mswm.utils.settings import LAGGED_ENSEMBLE_MEMBER_LAGS
# TODO replace with import of mswm.utils.settings.LAGGED_ENSEMBLE_MEMBER_LAGS
from consts import LAGGED_ENSEMBLE_MEMBER_LAGS, DEFAULT_MODEL_FORMULATION_ARGS


@dataclass
class ArgsKwargs:
    """Simple args list and kwargs dict to be passed later to parser.add_argument(*args, **kwargs)"""

    args: list
    kwargs: dict


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

MODEL_FORMULATION = ArgsKwargs(
    args=["-mf", "--model-formulation"],
    kwargs={
        "dest": "model_formulation_cli_args",
        "type": str,
        "nargs": 2,
        "required": False,
        "help": f"""Provide this multi-part argument to specify a non-default model formulation.

        This argument has 2 parts:
            1. models_csv : str
                Comma-separated value of models that make up the formulation. Default: {DEFAULT_MODEL_FORMULATION_ARGS[0]}
            2. use_root_zone : bool
                Boolean-like value for root zone choice. Use 0/1, false/true, no/yes. Default: {DEFAULT_MODEL_FORMULATION_ARGS[1]}
        """,
    },
)
