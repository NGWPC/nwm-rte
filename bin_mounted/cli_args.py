from dataclasses import dataclass

# from mswm.utils.settings import LAGGED_ENSEMBLE_MEMBER_LAGS
# TODO replace with import of mswm.utils.settings.LAGGED_ENSEMBLE_MEMBER_LAGS
from consts import LAGGED_ENSEMBLE_MEMBER_LAGS


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
