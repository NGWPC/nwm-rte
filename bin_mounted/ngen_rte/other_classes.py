"""Additional helper classes"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import pydantic.dataclasses
from pydantic import BaseModel, ConfigDict, Field

from ngen_rte import consts as c

pydantic_dataclass_strict = pydantic.dataclasses.dataclass(
    config=ConfigDict(strict=True, arbitrary_types_allowed=True, extra="forbid")
)


class BaseModelStrict(BaseModel):
    """pydantic BaseModel with strict type checking, arbitrary types allowed,
    and namespace validation (no unexpected / extra fields)."""

    model_config = ConfigDict(
        strict=True,
        arbitrary_types_allowed=True,
        extra="forbid",
    )


@dataclass
class TestPaths:
    """
    Paths dependent on calibration settings.
    If iterating over a list of objective functions or optimization algorithms,
    obj_func and optim_algo may need to be replaced on the fly during the iterations.
    """

    gage_id: str
    obj_func: c.CalObjective | None
    optim_algo: c.CalOptimizationAlgo | None
    global_domain: str
    forcing_static_dir: str

    def update_obj_func_and_optim_algo(
        self, obj_func: c.CalObjective, optim_algo: c.CalOptimizationAlgo
    ) -> None:
        """Informal setter for obj_func and optim_algo"""
        self.obj_func = obj_func
        self.optim_algo = optim_algo

    @property
    def fpp(self):
        """Build and return a ForcingProviderPaths instance to assist with setup."""
        return ForcingProviderPaths(
            global_domain=self.global_domain,
            forcing_static_dir=self.forcing_static_dir,
        )

    @property
    def dir_base(self) -> str:
        """The base directory of the model (can contain calibrations and forecasts)."""
        if not (self.obj_func and self.optim_algo):
            raise ValueError(
                "obj_func and optim_algo must be set before calling this method"
            )
        return f"{c.DEFAULT_MAIN_DIR}/{self.obj_func.value}_{self.optim_algo.value}/{self.fpp.formulation_name}/{self.gage_id}"

    @property
    def dir_input(self) -> str:
        """The Input directory of the model"""
        return f"{self.dir_base}/Input"

    @property
    def dir_output(self) -> str:
        """The Output directory of the model"""
        return f"{self.dir_base}/Output"

    @property
    def ngen_log_file(self) -> str:
        """The ngen.log file of the model"""
        return f"{self.dir_base}/logs/ngen.log"

    @property
    def calib_config_file(self) -> str:
        """Path to example input calibration config file"""
        return f"{self.dir_base}/configs/input_calibration_{c.FORCING_PROVIDER}.config"
        # return f"{self.dir_base}/configs/input_calibration_{c.FORCING_PROVIDER}_short.config"

    @property
    def fcst_config_file(self) -> str:
        """Path to example input forecast config file"""
        return f"{self.dir_base}/configs/input_forecast.config"

    @property
    def valid_yaml(self) -> str:
        """Path to validation yaml config file"""
        return f"{self.dir_output}/Validation_Run/{self.gage_id}_config_valid_best.yaml"


@pydantic_dataclass_strict
class ModelFormulation:
    """Each formulation is defined by comma-separated string of models, and a rootzone flag.
    i.e. some formulations involve running with or without rootzone enabled."""

    models_csv: str | None
    cfe_aet_rootzone: bool | str | None
    """This may start as a bool or a str, but then is converted to a bool during __post_init__."""

    def __post_init__(self):
        if self.models_csv is None:
            self.models_csv = c.DEFAULT_MODEL_FORMULATION_ARGS[0]
        if self.cfe_aet_rootzone is None:
            self.cfe_aet_rootzone = c.DEFAULT_MODEL_FORMULATION_ARGS[1]

        pattern = "^[a-z][a-z0-9-,]*[a-z]$"
        if not re.fullmatch(pattern, self.models_csv):
            raise ValueError(
                f"Expected models to match pattern {repr(pattern)} but got: {repr(self.models_csv)}"
            )
        self.cfe_aet_rootzone = booleanize(self.cfe_aet_rootzone)


class CalibTimeWindows(BaseModelStrict):
    """Calibration time windows defined by a start time
    and some timedelta offsets."""

    calib_sim_start: datetime = Field(default=c.CALIB_SIM_START_DEFAULT)
    calib_sim_duration: timedelta = Field(default=c.CALIB_SIM_DURATION_DEFAULT)
    # Delayed start from calibration simulation, for warmup
    calib_eval_delayment: timedelta = Field(default=c.CALIB_EVAL_DELAYMENT_DEFAULT)
    # Validation simulation starts before calibration simulation, by this amount
    valid_sim_advancement: timedelta = Field(default=c.VALID_SIM_ADVANCEMENT_DEFAULT)
    # Valid eval window cut short by this amount
    valid_eval_curtailment: timedelta = Field(default=c.VALID_EVAL_CURTAILMENT_DEFAULT)

    @property
    def calib_sim_end(self) -> datetime:
        """End of the calibration simulation window."""
        return self.calib_sim_start + self.calib_sim_duration

    @property
    def calib_eval_start(self) -> datetime:
        """Start of the calibration evaluation window."""
        return self.calib_sim_start + self.calib_eval_delayment

    @property
    def calib_eval_end(self) -> datetime:
        """End of the calibration evaluation window."""
        return self.calib_sim_end

    @property
    def valid_sim_start(self) -> datetime:
        """Start of the validation simulation window."""
        return self.calib_sim_start - self.valid_sim_advancement

    @property
    def valid_sim_end(self) -> datetime:
        """End of the validation simulation window."""
        return self.calib_sim_end

    @property
    def valid_eval_start(self) -> datetime:
        """Start of the validation evaluation window."""
        return self.calib_sim_start

    @property
    def valid_eval_end(self) -> datetime:
        """End of the validation evaluation window."""
        return self.calib_sim_end - self.valid_eval_curtailment

    @property
    def full_eval_start(self) -> datetime:
        """Start of the full evaluation window"""
        return self.calib_sim_start

    @property
    def full_eval_end(self) -> datetime:
        """End of the full evaluation window"""
        return self.calib_sim_end


class ForcingProviderPaths(BaseModelStrict):
    """Helper class for managing model paths."""

    global_domain: str
    forcing_static_dir: str

    @property
    def formulation_name(self) -> str:
        """Formulation name, as a part of the model path."""
        return f"test_{c.FORCING_PROVIDER}"


def booleanize(booly: str | bool) -> bool:
    """Convert the provided value to a boolean, parsing semantically no/0/false and yes/1/true. Case-insensitive."""
    if isinstance(booly, bool):
        return booly
    elif isinstance(booly, str):
        if booly.lower().strip() in ("no", "0", "false"):
            return False
        elif booly.lower().strip() in ("yes", "1", "true"):
            return True
        else:
            raise ValueError(
                f"Unexpected booly value: {repr(booly)}. Expected no/0/false or yes/1/true (case insensitive)."
            )
    else:
        raise TypeError(f"Unexpected booly type: {type(booly)}")
