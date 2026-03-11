from datetime import datetime, timedelta
from dataclasses import dataclass
import os
from typing import Literal

from mswm.utils.input_configuration import (
    InputConfig,
    ForcingConfig,
)
from mswm.utils import settings as mswm_settings

from pydantic import BaseModel, ConfigDict, Field

import consts as c


@dataclass
class TestPaths:
    """
    Paths dependent on calibration settings.
    If iterating over a list of objective functions or optimization algorithms,
    obj_func and optim_algo may need to be replaced on the fly during the iterations.
    """

    gage_id: str
    gage_vintage: str
    obj_func: c.CalObjective | None
    optim_algo: c.CalOptimizationAlgo | None
    global_domain: str
    forcing_provider: str
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
            forcing_provider=self.forcing_provider,
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
        return (
            f"{self.dir_base}/configs/input_calibration_{self.forcing_provider}.config"
        )
        # return f"{self.dir_base}/configs/input_calibration_{self.forcing_provider}_short.config"

    @property
    def fcst_config_file(self) -> str:
        """Path to example input forecast config file"""
        return f"{self.dir_base}/configs/input_forecast.config"

    @property
    def valid_yaml(self) -> str:
        """Path to validation yaml config file"""
        return f"{self.dir_output}/Validation_Run/{self.gage_id}_config_valid_best.yaml"


class RTECalibConfig(BaseModel):
    """Configuration class for building and running one calibration realization."""

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
    global_domain: str
    forcing_provider: str
    forcing_static_dir: str

    # Set after init
    gage_id: str = Field(init=False, default=None)
    gage_vintage: str = Field(init=False, default=None)
    ### For LSTM
    obs_dir: str | None = Field(init=False, default=None)
    nwmretro_file: str | None = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        errors = []

        self.gage_id, self.gage_vintage, errors_extend = parse_gage_id__gage_vintage(
            self.gage_id__gage_vintage
        )
        errors.extend(errors_extend)

        self.obs_dir, self.nwmretro_file, errors_extend = get_data_paths_for_lstm(
            self.global_domain,
            self.gage_id,
        )
        errors.extend(errors_extend)

        if errors:
            raise RuntimeError(errors)


class RTEForecastConfig(BaseModel):
    """Configuration class for building and running one forecast realization."""

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    delete_scratch_and_mesh_first: bool
    delete_forcing_raw_input_first: bool
    ### These calibration parameters affect directory path
    objective_function: c.CalObjective
    optimization_algorithm: c.CalOptimizationAlgo
    gage_id: str
    global_domain: str
    forcing_static_dir: str
    forcing_provider: str
    cycle_datetime: datetime | None
    cold_start_datetime: datetime | None
    forcing_configuration: str
    fcst_run_name: str
    nprocs: int = Field(ge=1)

    # Derived paths (not passed to __init__)
    run_dir_base: str = Field(init=False, default=None)
    run_dir_input: str = Field(init=False, default=None)
    run_dir_output: str = Field(init=False, default=None)
    ngen_log_file: str = Field(init=False, default=None)
    valid_best_yaml: str = Field(init=False, default=None)

    # Other derived attrs (not passed to __init__)
    realization_builder_kwargs: dict = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        self.run_dir_base = f"{c.DEFAULT_MAIN_DIR}/{self.objective_function.value}_{self.optimization_algorithm.value}/test_{self.forcing_provider}/{self.gage_id}"
        if not os.path.isdir(self.run_dir_base):
            msg = f"Not a directory: {repr(self.run_dir_base)}. Please review choices for objective function, optimization algorithm, and gage, which affect this path."
            raise NotADirectoryError(msg)

        self.run_dir_input = f"{self.run_dir_base}/Input"
        self.run_dir_output = f"{self.run_dir_base}/Output"
        self.ngen_log_file = f"{self.run_dir_base}/logs/ngen.log"
        self.valid_best_yaml = f"{self.run_dir_output}/Validation_Run/{self.gage_id}_config_valid_best.yaml"

        self.realization_builder_kwargs = self._make_realization_builder_kwargs()

    def _make_realization_builder_kwargs(self) -> dict:
        """Build and return a dictionary for creating a RealizationBuilder instance."""
        fpp = ForcingProviderPaths(
            forcing_provider=self.forcing_provider,
            global_domain=self.global_domain,
            forcing_static_dir=self.forcing_static_dir,
        )
        realization_kwargs = {
            # "input_path": forecast_vars.forecast_input_config,
            "valid_yaml": self.valid_best_yaml,
            "fcst_run_name": self.fcst_run_name,
            "config_overrides": InputConfig(
                Forcing=ForcingConfig(
                    forcing_provider=fpp.forcing_provider,
                    forcing_dir=fpp.get_forcing_dir(gage_id=self.gage_id),
                    forcing_template_dir=c.FORCING_TEMPLATE_DIR,
                    root_dir=c.FORCING_ROOT_DIR,
                    forcing_configuration=self.forcing_configuration,
                    cycle_datetime=self.cycle_datetime.strftime(
                        mswm_settings.DEFAULT_DATETIME_FORMAT
                    ),
                    cold_start_datetime=self.cold_start_datetime.strftime(
                        mswm_settings.DEFAULT_DATETIME_FORMAT
                    )
                    if self.cold_start_datetime
                    else None,
                    global_domain=self.global_domain,
                    forcing_static_dir=self.forcing_static_dir,
                )
            ),
        }
        return realization_kwargs


class RTETestConfig(BaseModel):
    """Configuration class for building and running a set of test realizations."""

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
    global_domain: str
    forcing_provider: str
    forcing_static_dir: str
    noop: bool

    # Set after init
    gage_id: str = Field(init=False, default=None)
    gage_vintage: str = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        errors = []

        self.gage_id, self.gage_vintage, errors_extend = parse_gage_id__gage_vintage(
            self.gage_id__gage_vintage
        )
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

    def get_calib_permutations(
        self,
    ) -> list[tuple[c.CalObjective, c.CalOptimizationAlgo, TestPaths]]:
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
                ret.append(
                    (
                        obj_func,
                        optim_algo,
                        TestPaths(
                            self.gage_id,
                            self.gage_vintage,
                            obj_func,
                            optim_algo,
                            self.global_domain,
                            self.forcing_provider,
                            self.forcing_static_dir,
                        ),
                    )
                )
        return ret


def parse_gage_id__gage_vintage(
    gage_id__gage_vintage: tuple[str, str],
) -> tuple[str | None, str | None, list[Exception]]:
    """Parse the provided string and split it into two strings: gage_id and gage_vintage"""
    errors: list[Exception] = []
    gage_id, gage_vintage = gage_id__gage_vintage

    if gage_id != gage_id.strip():
        errors.append(
            ValueError(f"Whitespace found on end of gage_id: {repr(gage_id)}")
        )
        gage_id = None

    if gage_vintage != gage_vintage.strip():
        errors.append(
            ValueError(f"Whitespace found on end of gage_vintage: {repr(gage_vintage)}")
        )
        gage_vintage = None

    return gage_id, gage_vintage, errors


def parse_fcst_run_name(fcst_run_name: str) -> list[Exception]:
    """Validate the provided forecast run name, and return a list of errors."""
    errors: list[Exception] = []
    if fcst_run_name != fcst_run_name.strip():
        errors.append(
            ValueError(
                f"Whitespace found on end of fcst_run_name: {repr(fcst_run_name)}"
            )
        )
    return errors


class ForcingProviderPaths(BaseModel):
    """Helper class for managing model paths."""

    model_config = ConfigDict(strict=True)
    forcing_provider: Literal["csv", "bmi"]
    global_domain: str  # e.g. CONUS. TODO restrict choices
    forcing_static_dir: str

    def get_forcing_dir(self, gage_id: str | None) -> str | None:
        if self.forcing_provider == "csv":
            if not gage_id:
                raise ValueError(
                    "Gage ID must be provided when forcing_provider == 'csv'"
                )
            return c.CSV_FORCING_DIR_FORMAT.format(
                global_domain=self.global_domain, gage_id=gage_id
            )
        elif self.forcing_provider == "bmi":
            return self.forcing_static_dir
        else:
            raise ValueError(f"Unexpected forcing_provider: {self.forcing_provider}")

    @property
    def formulation_name(self) -> str:
        """Formulation name, as a part of the model path."""
        return f"test_{self.forcing_provider}"


class CalibTimeWindows(BaseModel):
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


def get_data_paths_for_lstm(
    global_domain: str,
    gage_id: str,
) -> tuple[str | None, str | None, list[Exception]]:
    """Build and return two data paths needed for LSTM model,
    as well as a list of errors encountered during this function.
    Return None for obs_dir and nwmretro_file if not LSTM."""

    errors: list[Exception] = []

    if "lstm" in c.MODELS.lower():
        obs_dir = find_obs_dir(global_domain, gage_id)
        nwmretro_file = f"{c.NWM_RETRO_STREAMFLOW_DIR}/{gage_id}.csv"
        if not os.path.exists(obs_dir):
            errors.append(NotADirectoryError(obs_dir))
        if not os.path.exists(nwmretro_file):
            errors.append(FileNotFoundError(nwmretro_file))
    else:
        obs_dir = None
        nwmretro_file = None

    return obs_dir, nwmretro_file, errors


def find_obs_dir(global_domain: str, gage_id: str) -> str:
    """Search the grandparent directory of observational flow csv files to determine
    the directory that contains one of them.  Assert that only one such csv file is found.
    If multiple are found, then this function needs to be reworked to handle more complex
    situations, such as multiple vintages of this data existing on disk."""
    grandparent = (
        f"{c.HYDROFABRIC_DIR}/2.1/{global_domain}/{gage_id}/OBSERVATIONAL/USGS"
    )
    candidate_csvs = []
    for root, dirs, files in os.walk(grandparent):
        dirs.sort()
        files.sort()
        for fn in files:
            if fn.endswith(".csv"):
                candidate_csvs.append(os.path.join(root, fn))
    if len(candidate_csvs) != 1:
        raise ValueError(
            f"Expected to find 1 candidate csv for observational forcing, got {len(candidate_csvs)}: {candidate_csvs}"
        )
    obs_dir = os.path.dirname(candidate_csvs[0])
    return obs_dir
