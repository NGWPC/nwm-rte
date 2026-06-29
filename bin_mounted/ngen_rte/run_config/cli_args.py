"""CLI args for executable Python scripts/modules.

The instances of ArgsKwargs defined in this file are auto-discovered by add_args_for_script().
"""

import argparse
import sys
from dataclasses import dataclass
from enum import StrEnum

from mswm.utils.settings import DEFAULT_DATETIME_FORMAT, LAGGED_ENSEMBLE_MEMBER_LAGS
from ngen_rte import consts as c
from ngen_rte.utils import (
    datetime_from_str,
    datetime_type,
    str_from_datetime,
    timedelta_from_effective_days,
    timedelta_from_pandas_str,
)


class Script(StrEnum):
    """Enum used to classify which script(s) each CLI arg should be added to, to keep the args lists DRY."""

    DEFAULT = "run_default"
    REGIONALIZATION = "run_regionalization_standalone"
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
    """Auto-discover the instances of ArgsKwargs in this file and add them to the provided parser,
    if they match the type of Script provided."""
    current_module = sys.modules[__name__]
    for symbol_name in dir(current_module):
        item = getattr(current_module, symbol_name)
        if type(item) is ArgsKwargs:
            if script in item.scripts or Script.ALL in item.scripts:
                add_arg(parser, item)


class HelpFormatter(
    argparse.RawTextHelpFormatter,
    argparse.ArgumentDefaultsHelpFormatter,
):
    """Custom help formatter"""

    def _format_action(self, action):
        r"""Add \n between each argument."""
        return super()._format_action(action) + "\n"

    def _format_action_invocation(self, action):
        """Remove metavar and add [bool switch] for args that are boolean flags."""
        if action.option_strings:
            flags = ", ".join(action.option_strings)
            # Add type to flags line
            flags = f"{flags} : {self._type_label(action)}"
            # Add default value to flags line
            if action.default is not argparse.SUPPRESS:
                flags = f"{flags} default={repr(action.default)}"
            return flags
        return ""

    @staticmethod
    def _type_label(action: argparse.Action) -> str | None:
        if isinstance(action, argparse._StoreTrueAction):
            return "bool-switch(store-true)"
        type_name = getattr(getattr(action, "type", None), "__name__", None)
        if type_name == "str_to_bool":
            type_name = "bool"
        return f"type={type_name}"

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


def add_arg(parser: argparse.ArgumentParser, arg: ArgsKwargs) -> None:
    """Helper function to add a CLI argument to an existing argparse parser."""
    parser.add_argument(*arg.args, **arg.kwargs)


ENVIRONMENT = ArgsKwargs(
    args=["-e", "--environment"],
    kwargs={
        "type": str,
        "default": c.DEFAULT_ENVIRONMENT,
        "choices": ["test", "oe"],
        "help": "Operating environment. Affects name of server used to fetch input data. Passed to MSWM GeneralConfig.",
    },
    scripts=[Script.ALL],
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

# Note: This is defaulted to c.DEFAULT_GAGE_ID in configs.py,
# after checking that the user does not supply both --gage_id and --vpu_id
GAGE_ID = ArgsKwargs(
    args=["-g", "--gage_id"],
    kwargs={
        "type": str,
        "default": None,
        "help": f"Gage ID. CLI defaults to None, but ``RTEBaseConfig.model_post_init`` effectively defaults it to {c.DEFAULT_GAGE_ID} when -v / --vpu is not provided.",
    },
    scripts=[Script.ALL],
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
    scripts=[
        Script.FORECAST,
        Script.CALIBRATION,
        Script.DEFAULT,
        Script.REGIONALIZATION,
    ],
)

FCST_RUN_NAME = ArgsKwargs(
    args=["-rname", "--fcst_run_name"],
    kwargs={
        "type": str,
        "default": c.DEFAULT_FORECAST_RUN_NAME,
        "help": "Forecast run name.",
    },
    scripts=[Script.FORECAST, Script.DEFAULT, Script.REGIONALIZATION, Script.TESTS],
)

TIMESTAMP_RUN_NAME_SUFFIX = ArgsKwargs(
    args=["-ts", "--timestamp_run_name"],
    kwargs={
        "dest": "add_timestamp_to_run_name",
        "action": "store_true",
        "help": "If provided, add a timestamp suffix to the run name.",
    },
    scripts=[Script.FORECAST, Script.DEFAULT, Script.REGIONALIZATION],
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
    scripts=[Script.FORECAST, Script.DEFAULT, Script.REGIONALIZATION],
)

COLD_START_DATETIME = ArgsKwargs(
    args=["-csdt", "--cold_start_datetime"],
    kwargs={
        "type": datetime_type,
        "help": f"""If provided, a cold-start realization will be ran prior to the forecast,
and this value will be the start time for the cold-start.
Format: {repr(DEFAULT_DATETIME_FORMAT.replace("%", "%%"))}.""",
    },
    scripts=[Script.FORECAST],
)

NWM_OUTPUT_VARIABLES = ArgsKwargs(
    args=["-nwmout", "--nwm_output_vars_true"],
    kwargs={
        "dest": "nwm_output_vars",
        "action": "store_true",
        "help": "If provided, NWMOutputConfig.nwm_output_variables will be set to True",
    },
    scripts=[Script.FORECAST, Script.DEFAULT, Script.REGIONALIZATION],
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
        Name of the ensemble member. Choose from: {split_iter_to_chunked_str(list(LAGGED_ENSEMBLE_MEMBER_LAGS))}
    2. open_loop_state : str (optional)
        Path to an existing open-loop state file.
        To omit, provide an empty string for this part.
    3. closed_loop_state : str (optional)
        Path to an existing closed-loop state file.
        To omit, provide an empty string for this part.

To run a lagged ensemble member without the optional parts,
provide them as empty strings e.g. `-le 'mem2' '' ''`.""",
    },
    scripts=[Script.FORECAST, Script.DEFAULT, Script.REGIONALIZATION],
)

OBJECTIVE_FUNCTION = ArgsKwargs(
    args=["-ofunc", "--objective_function"],
    kwargs={
        "type": c.CalObjective,
        "help": """Objective function of previously-ran calibration realization
for basis of forecast. Affects directory path.""",
        "default": c.CALIB_OBJECTIVE_FUNCTION,
    },
    scripts=[Script.FORECAST, Script.CALIBRATION],
)

OPTIMIZATION_ALGORITHM = ArgsKwargs(
    args=["-optalgo", "--optimization_algorithm"],
    kwargs={
        "type": c.CalOptimizationAlgo,
        "help": """Optimization algorithm of previously-ran calibration realization
for basis of forecast. Affects directory path.""",
        "default": c.CALIB_OPTIMIZATION_ALGO,
    },
    scripts=[Script.FORECAST, Script.CALIBRATION],
)

CALIB_SIM_START_TIME = ArgsKwargs(
    args=["-start", "--calib_sim_start"],
    kwargs={
        "type": datetime_from_str,
        "required": False,
        "default": str_from_datetime(c.CALIB_SIM_START_DEFAULT),
        "help": "Start time for the calibration realization",
    },
    scripts=[Script.CALIBRATION],
)

CALIB_DURATION = ArgsKwargs(
    args=["-dur", "--duration"],
    kwargs={
        "type": timedelta_from_effective_days,
        "default": c.CALIB_SIM_DURATION_DEFAULT,
        "help": """Duration of calibration/default/regionalization realization. Units: days (integer). Ignored by default/regionalization realization when a realtime forcing configuration is chosen.""",
    },
    scripts=[Script.CALIBRATION, Script.DEFAULT, Script.REGIONALIZATION],
)

MODELS_RZ = ArgsKwargs(
    args=["-rz", "--root-zone"],
    kwargs={
        "dest": "model_formulation_cli_rootzone",
        "type": str,
        "required": False,
        "default": str(c.DEFAULT_MODEL_FORMULATION_ARGS[1]),
        "help": """Provided value is converted to Boolean and passed as `cfe_aet_rootzone`.
The value should be either true/yes/1 or false/no/0.
Can be used in conjunction with ["-mf", "--model-formulation"].""",
    },
    scripts=[Script.CALIBRATION, Script.DEFAULT],
)

MODELS_CSV = ArgsKwargs(
    args=["-mf", "--model-formulation"],
    kwargs={
        "dest": "model_formulation_cli_csv",
        "type": str,
        "required": False,
        "default": str(c.DEFAULT_MODEL_FORMULATION_ARGS[0]),
        "help": """Provide this argument to specify a non-default model formulation.
The value should be a comma-separated string of models that make up the formulation.
Can be used in conjunction with ["-rz", "--root-zone"].""",
    },
    scripts=[Script.CALIBRATION, Script.DEFAULT],
)

CALIB_WORKER_NAME = ArgsKwargs(
    args=["-wrkr", "--worker_name"],
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
    scripts=[Script.CALIBRATION, Script.DEFAULT, Script.REGIONALIZATION, Script.TESTS],
)

CHECKPOINT_INTERVAL = ArgsKwargs(
    args=["-c", "--checkpoint_interval"],
    kwargs={
        "type": int,
        "default": None,
        "help": "Checkpointing interval in integer number of timesteps. If provided, enables checkpointing during the run.",
    },
    scripts=[Script.DEFAULT, Script.REGIONALIZATION],
)

CHECKPOINT_INTERVAL = ArgsKwargs(
    args=["-cd", "--checkpoint_dir"],
    kwargs={
        "type": str,
        "default": None,
        "help": "Directory to save checkpoint states. Defaults to work_dir>/checkpoint/ in msw-mgr.",
    },
    scripts=[Script.DEFAULT, Script.REGIONALIZATION],
)

LOAD_STATE_FROM = ArgsKwargs(
    args=["-lsf", "--load_state_from"],
    kwargs={
        "type": str,
        "default": None,
        "help": "Path to existing state file to load at start of run.",
    },
    scripts=[Script.DEFAULT, Script.FORECAST, Script.REGIONALIZATION],
)

SAVE_STATE = ArgsKwargs(
    args=["-ss", "--save_state"],
    kwargs={
        "action": "store_true",
        "help": "If provided, save the model state at the end of the run.",
    },
    scripts=[Script.DEFAULT, Script.FORECAST, Script.REGIONALIZATION],
)

SAVE_STATE_DIR = ArgsKwargs(
    args=["-ssd", "--save_state_dir"],
    kwargs={
        "type": str,
        "default": None,
        "help": "Directory to save model state at end of run. Defaults in <work_dir>/state_save/ in msw-mgr.",
    },
    scripts=[Script.DEFAULT, Script.FORECAST, Script.REGIONALIZATION],
)

VPU = ArgsKwargs(
    args=["-v", "--vpu"],
    kwargs={
        "type": str,
        "default": None,
        "help": "VPU identifier. When provided, sets subset_type to 'vpu'. Cannot be used with gage_id.",
    },
    scripts=[Script.DEFAULT, Script.REGIONALIZATION],
)

LOOKBACK = ArgsKwargs(
    args=["-lb", "--lookback"],
    kwargs={
        "type": int,
        "default": None,
        "help": """If provided, override the forcing template `LookBack` value (in minutes).
This controls the analysis (AnA) simulation window for AnA forcing configurations,
e.g. 'standard_ana' or 'extended_ana'. The simulated window length in hours is
`LookBack/60 - 1`, ending at the cycle datetime (-dt). Ignored if not provided.""",
    },
    scripts=[Script.DEFAULT, Script.REGIONALIZATION],
)

FORM_ASSIGN_FILE = ArgsKwargs(
    args=["-faf", "--form_assign_file"],
    kwargs={
        "type": str,
        "required": True,
        "help": "Path to file containing formulation assignments for catchments.",
    },
    scripts=[Script.REGIONALIZATION],
)

CAT_GRP_FILE = ArgsKwargs(
    args=["-cgf", "--cat_grp_file"],
    kwargs={
        "type": str,
        "required": True,
        "help": "Path to file containing catchment groupings.",
    },
    scripts=[Script.REGIONALIZATION],
)

OUTPUT_FORMAT = ArgsKwargs(
    args=["-outfmt", "--output_format"],
    kwargs={
        "type": str,
        "nargs": "+",
        "default": c.OUTPUT_FORMAT_DEFAULT,
        "help": """Output format(s) for NWM output variables. Accepts 'CSV', 'NetCDF' or both.
Provide as space-separated values e.g. -outfmt CSV NetCDF.""",
    },
    scripts=[
        Script.FORECAST,
        Script.CALIBRATION,
        Script.DEFAULT,
        Script.REGIONALIZATION,
    ],
)
