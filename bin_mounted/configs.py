from datetime import datetime, timedelta
from dataclasses import dataclass

from execution_tests import (
    TestsManager, TestPaths
)
from pseudocode import SavedState_Pseudo, StateManager_Pseudo
from pydantic import BaseModel, ConfigDict, Field

import consts as c


class RTECalibConfig(BaseModel):
    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    delete_scratch_and_mesh_first: bool
    delete_forcing_raw_input_first: bool
    objective_function: c.CalObjective
    optimization_algorithm: c.CalOptimizationAlgo
    nprocs: int = Field(ge=1)
    gage_id__gage_vintage: list[str] = Field(min_length=2, max_length=2)
    calib_sim_start: datetime
    calib_sim_duration: timedelta
    calib_eval_delayment: timedelta
    valid_sim_advancement: timedelta
    valid_eval_curtailment: timedelta
    forcing_source: str
    forcing_region: str

    # Set after init
    gage_id: str = Field(init=False, default=None)
    gage_vintage: str = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        errors = []

        gage_id, gage_vintage, errors_extend = parse_gage_id__gage_vintage(
            self.gage_id__gage_vintage
        )
        errors.extend(errors_extend)

        if errors:
            raise RuntimeError(errors)

        self.gage_id = gage_id
        self.gage_vintage = gage_vintage


class RTETestConfig(BaseModel):
    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    delete_scratch_and_mesh_first: bool
    delete_forcing_raw_input_first: bool
    skip_forecast: bool
    quit_forecast_after_forcing_running: bool
    quit_forecast_after_duration: float | None = Field(ge=0)
    do_calibration: bool
    quit_calibration_after_duration: float | None = Field(ge=0)
    # Replaced with full list when do_all_objective_functions = True
    objective_functions: list[c.CalObjective]
    do_all_objective_functions: bool
    # Replaced with full list when do_all_optimization_algorithms = True
    optimization_algorithms: list[c.CalOptimizationAlgo]
    do_all_optimization_algorithms: bool
    do_all_forcing_configs: bool
    do_coldstart: bool
    fcst_run_name: str
    nprocs: int = Field(ge=1)
    gage_id__gage_vintage: list[str] = Field(min_length=2, max_length=2)
    forcing_region: str
    noop: bool

    # Set after init
    gage_id: str = Field(init=False, default=None)
    gage_vintage: str = Field(init=False, default=None)
    tests_manager: TestsManager = Field(init=False, default=None)
    state_manager: StateManager_Pseudo = Field(init=False, default=None)  # TODO pseudocode for now for states.

    def model_post_init(self, __context) -> None:
        errors = []

        gage_id, gage_vintage, errors_extend = parse_gage_id__gage_vintage(self.gage_id__gage_vintage)
        errors.extend(errors_extend)

        errors_extend = parse_fcst_run_name(self.fcst_run_name)
        errors.extend(errors_extend)

        if self.do_all_objective_functions:
            self.objective_functions = list(c.CalObjective)
        if self.do_all_optimization_algorithms:
            self.optimization_algorithms = list(c.CalOptimizationAlgo)

        if self.do_all_forcing_configs:
            if self.skip_forecast and (not self.do_coldstart):
                errors.append(
                    ValueError(
                        f"When do_all_forcing_configs={self.do_all_forcing_configs}, must have coldstart and/or forecast enabled."
                    )
                )

        if errors:
            raise RuntimeError(errors)

        self.gage_id = gage_id
        self.gage_vintage = gage_vintage
        self.tests_manager = TestsManager()
        self.state_manager = StateManager_Pseudo()

    def get_calib_permutations(self) -> list[tuple[c.CalObjective, c.CalOptimizationAlgo, TestPaths]]:
        """Returns the permutations of objective function and optimization algorithm specified in the config, as well as a TestPaths instance for each.
        If only_first, then only the first permutation will be returned. Else all permutations will be returned."""
        ret = []
        for obj_func in self.objective_functions:
            if obj_func == c.CalOptimizationAlgo.none:
                # TODO enable objective function "none" for supported circumstances
                continue
            for optim_algo in self.optimization_algorithms:
                if optim_algo == c.CalOptimizationAlgo.none:
                    # TODO enable optimization algo "none" for supported circumstances
                    continue
                ret.append((obj_func, optim_algo, TestPaths(self.gage_id, self.gage_vintage, obj_func, optim_algo)))
        return ret


def parse_gage_id__gage_vintage(gage_id__gage_vintage: tuple[str, str]) -> tuple[str | None, str | None, list[Exception]]:
    errors: list[Exception] = []
    gage_id, gage_vintage = gage_id__gage_vintage

    if gage_id != gage_id.strip():
        errors.append(ValueError(f"Whitespace found on end of gage_id: {repr(gage_id)}"))
        gage_id = None

    if gage_vintage != gage_vintage.strip():
        errors.append(ValueError(f"Whitespace found on end of gage_vintage: {repr(gage_vintage)}"))
        gage_vintage = None

    return gage_id, gage_vintage, errors


def parse_fcst_run_name(fcst_run_name: str) -> list[Exception]:
    errors: list[Exception] = []
    if fcst_run_name != fcst_run_name.strip():
        errors.append(ValueError(f"Whitespace found on end of fcst_run_name: {repr(fcst_run_name)}"))
    return errors
