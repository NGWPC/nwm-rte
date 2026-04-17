from datetime import datetime, timedelta
from dataclasses import dataclass
import os
import re
from typing import Literal

from mswm.utils.settings import LAGGED_ENSEMBLE_MEMBER_LAGS
from mswm.utils.input_configuration import (
    InputConfig,
    GeneralConfig,
    ModulePropertiesConfig,
    ForcingConfig,
    DataFileConfig,
    ParallelConfig,
)
from mswm.utils import settings as mswm_settings
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT as DDF

from pydantic import BaseModel, ConfigDict, Field

import consts as c
from utils import make_wcoss_path_symlinks


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


class RTESetup(BaseModel):
    """Used to set up a RTE run. Triggers certain setup actions, such as creation of WCOSS-path symlinks.
    Classes that inherit from this should call super().model_post_init(__context) inside their own
    model_post_init() method, if they have that method also defined in the child."""

    def model_post_init(self, __context) -> None:
        make_wcoss_path_symlinks()

    def _parse_lagged_ensemble_args(self):
        """Break up the multipart lagged ensemble arg into distinct args and set them.
        Called by child classes which define the necessary attributes."""
        if self.lagged_ensemble_args:
            if self.forcing_configuration != "medium_range":
                raise ValueError(
                    f"lagged ensemble only supported for medium_range, but forcing configuration {repr(self.forcing_configuration)} was provided"
                )

            self.use_lagged_ensemble = True

            member_name, open_ls, closed_ls = self.lagged_ensemble_args

            self.lagged_ens_mem = member_name if member_name.strip() else None
            self.forcing_lag = LAGGED_ENSEMBLE_MEMBER_LAGS[self.lagged_ens_mem]
            self.le__open_loop_state = open_ls if open_ls.strip() else None
            self.le__closed_loop_state = closed_ls if closed_ls.strip() else None

            if self.lagged_ens_mem not in LAGGED_ENSEMBLE_MEMBER_LAGS:
                raise KeyError(
                    f"Invalid lagged ensemble member {repr(self.lagged_ens_mem)} (choose from: {list(LAGGED_ENSEMBLE_MEMBER_LAGS)})"
                )

        if self.le__open_loop_state or self.le__closed_loop_state:
            raise NotImplementedError(
                "Lagged ensemble args for Open Loop State and Closed Loop State are not yet implemented in nwm-rte (should be provided as empty strings for now)"
            )


class RTEDefaultConfig(RTESetup):
    """Configuration class for building and running one default realization
    (realtime forcing configuration or historical / retrospective forcing configuration)."""

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    delete_scratch_and_mesh_first: bool
    delete_forcing_raw_input_first: bool
    gage_id__gage_vintage: list[str] = Field(min_length=2, max_length=2)
    global_domain: str
    forcing_static_dir: str
    forcing_provider: str
    cycle_datetime: datetime
    historical_sim_duration: timedelta | None
    forcing_configuration: str
    fcst_run_name: str
    nprocs: int = Field(ge=1)

    # Set after init
    gage_id: str = Field(init=False, default=None)
    gage_vintage: str = Field(init=False, default=None)
    realtime_mode: bool = Field(init=False, default=None)

    # Other derived attrs (not passed to __init__)
    realization_builder_kwargs: dict = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTESetup's post init

        errors = []

        if (
            self.forcing_configuration
            not in c.FORECAST_FORCING_CONFIGURATION_TYPES__ALL
        ):
            self.realtime_mode = False
        else:
            self.realtime_mode = True

        self.gage_id, self.gage_vintage, errors_extend = parse_gage_id__gage_vintage(
            self.gage_id__gage_vintage
        )
        errors.extend(errors_extend)

        if (not self.realtime_mode) and (not self.historical_sim_duration):
            errors.extend(
                [
                    f"Forcing configuration {repr(self.forcing_configuration)} is *not* realtime, and requires that CLI arg -dur aka --historical_sim_duration is provided, but it was not."
                ]
            )
        if self.realtime_mode and self.historical_sim_duration:
            errors.extend(
                [
                    f"Forcing configuration {repr(self.forcing_configuration)} *is* realtime, but CLI arg -dur aka --historical_sim_duration was also provided (it should not be)."
                ]
            )

        if errors:
            raise RuntimeError(errors)

        self.realization_builder_kwargs = self._make_realization_builder_kwargs()

    def _make_realization_builder_kwargs(self) -> dict:
        """Build and return a dictionary for creating a RealizationBuilder instance."""
        fpp = ForcingProviderPaths(
            forcing_provider=self.forcing_provider,
            global_domain=self.global_domain,
            forcing_static_dir=self.forcing_static_dir,
        )

        windows = CalibTimeWindows(
            calib_sim_start=self.cycle_datetime,
            calib_sim_duration=self.historical_sim_duration
            if self.historical_sim_duration
            else c.CALIB_SIM_DURATION_DEFAULT,
            calib_eval_delayment=c.CALIB_EVAL_DELAYMENT_DEFAULT,
            valid_sim_advancement=c.VALID_SIM_ADVANCEMENT_DEFAULT,
            valid_eval_curtailment=c.VALID_EVAL_CURTAILMENT_DEFAULT,
        )

        if self.realtime_mode:
            start_period = None
            end_period = None
        else:
            start_period = windows.calib_eval_start.strftime(DDF)
            end_period = windows.calib_eval_end.strftime(DDF)

        cycle_datetime = self.cycle_datetime.strftime(
            mswm_settings.DEFAULT_DATETIME_FORMAT
        )

        realization_kwargs = {
            # "input_path": forecast_vars.forecast_input_config,
            "fcst_run_name": self.fcst_run_name,
            "config_overrides": InputConfig(
                General=GeneralConfig(
                    basin=self.gage_id,
                    run_type="default",
                    models=c.MODELS,
                    formulation=fpp.formulation_name,
                    main_dir=c.DEFAULT_MAIN_DIR,
                    start_period=start_period,
                    end_period=end_period,
                    output_precip=True,
                    output_swe=True,
                    output_sm=True,
                    domain=self.global_domain.lower(),
                ),
                ModuleProperties=ModulePropertiesConfig(),
                Forcing=ForcingConfig(
                    forcing_provider=fpp.forcing_provider,
                    forcing_dir=fpp.get_forcing_dir(gage_id=self.gage_id),
                    forcing_template_dir=c.FORCING_TEMPLATE_DIR,
                    root_dir=c.FORCING_ROOT_DIR,
                    forcing_configuration=self.forcing_configuration,
                    cycle_datetime=cycle_datetime,
                    cold_start_datetime=None,
                    global_domain=self.global_domain,
                    forcing_static_dir=self.forcing_static_dir,
                    scratch_dir_override=c.SCRATCH_DIR_OVERRIDE,
                    input_forcing_dirs_override_root=c.INPUT_FORCING_DIRS_OVERRIDE_ROOT,
                    forcing_product_versions=c.FORCING_PRODUCT_VERSIONS_DICT,
                ),
                DataFile=DataFileConfig(
                    **(
                        c.DATAFILE_LIBS
                        | {
                            "hydrofab_file": f"{c.HYDROFABRIC_DIR}/2.2/{self.global_domain}/{self.gage_id}/GEOPACKAGE/USGS/{self.gage_vintage}/gauge_{self.gage_id}.gpkg",
                        }
                    ),
                ),
                Parallel=make_parallel_config(self.nprocs),
            ),
        }
        return realization_kwargs


class RTECalibConfig(RTESetup):
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
    worker_name: str | None

    # Set after init
    gage_id: str = Field(init=False, default=None)
    gage_vintage: str = Field(init=False, default=None)
    obs_dir: str | None = Field(init=False, default=None)
    nwmretro_file: str | None = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTESetup's post init

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


class RTEForecastConfig(RTESetup):
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
    # For medium-range lagged ensemble
    lagged_ensemble_args: list[str] | None = Field(
        min_length=3, max_length=3
    )

    # Derived paths (not passed to __init__)
    run_dir_base: str = Field(init=False, default=None)
    run_dir_input: str = Field(init=False, default=None)
    run_dir_output: str = Field(init=False, default=None)
    ngen_log_file: str = Field(init=False, default=None)
    valid_best_yaml: str = Field(init=False, default=None)
    # For lagged ensemble
    use_lagged_ensemble: bool | None = Field(init=False, default=False)
    lagged_ens_mem: str | None = Field(init=False, default=None)
    forcing_lag: str | None = Field(init=False, default=None)
    le__open_loop_state: str | None = Field(init=False, default=None)
    le__closed_loop_state: str | None = Field(init=False, default=None)

    # Other derived attrs (not passed to __init__)
    realization_builder_kwargs: dict = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTESetup's post init

        self.run_dir_base = f"{c.DEFAULT_MAIN_DIR}/{self.objective_function.value}_{self.optimization_algorithm.value}/test_{self.forcing_provider}/{self.gage_id}"
        if not os.path.isdir(self.run_dir_base):
            msg = f"Not a directory: {repr(self.run_dir_base)}. Please review choices for objective function, optimization algorithm, and gage, which affect this path."
            raise NotADirectoryError(msg)

        self.run_dir_input = f"{self.run_dir_base}/Input"
        self.run_dir_output = f"{self.run_dir_base}/Output"
        self.ngen_log_file = f"{self.run_dir_base}/logs/ngen.log"
        self.valid_best_yaml = f"{self.run_dir_output}/Validation_Run/{self.gage_id}_config_valid_best.yaml"

        super()._parse_lagged_ensemble_args()
        self._make_realization_builder_kwargs()

    def _make_realization_builder_kwargs(self) -> None:
        """Build and set a dictionary for creating a RealizationBuilder instance."""
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
                    scratch_dir_override=c.SCRATCH_DIR_OVERRIDE,
                    input_forcing_dirs_override_root=c.INPUT_FORCING_DIRS_OVERRIDE_ROOT,
                    forcing_product_versions=c.FORCING_PRODUCT_VERSIONS_DICT,
                ),
                Parallel=make_parallel_config(self.nprocs),
            ),
            # Lagged ensemble args
            "use_lagged_ens": self.use_lagged_ensemble,
            "lagged_ens_mem": self.lagged_ens_mem,
            "forcing_lag": self.forcing_lag,
        }
        self.realization_builder_kwargs = realization_kwargs


class RTETestConfig(RTESetup):
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
        super().model_post_init(__context)  # Call RTESetup's post init

        errors = []

        if self.quit_forecast_after_forcing_running:
            errors.append(
                RuntimeError(
                    "quit_forecast_after_forcing_running is currently not allowed, pending updates."
                )
            )

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


def make_parallel_config(nprocs: int) -> ParallelConfig:
    """Build and return the ParallelConfig instance."""
    if nprocs and nprocs > 1:
        parallel = ParallelConfig(
            parallel_ngen_exe=c.NGEN_BIN__LINK,
            partition_generator_exe=c.PARTITION_GENERATOR_BIN__LINK,
            nprocs=nprocs,
        )
    else:
        parallel = ParallelConfig(nprocs=nprocs)
    return parallel


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
    """Search the grandparent directory of observed flow csv files to determine
    the directory that contains one of them.  Assert that only one such csv file is found.
    If multiple are found, then this function needs to be reworked to handle more complex
    situations, such as multiple vintages of this data existing on disk."""
    grandparent = f"{c.DEFAULT_MAIN_DIR}/data/streamflow_observations/{global_domain}"
    print(f"Searching directory for observed flow files: {grandparent}")
    candidate_csvs = []
    for root, dirs, files in os.walk(grandparent):
        dirs.sort()
        files.sort()
        for fn in files:
            pattern = f"^{gage_id}_hourly_discharge.csv$"
            if re.fullmatch(pattern, fn):
                candidate_csvs.append(os.path.join(root, fn))
    if len(candidate_csvs) != 1:
        raise ValueError(
            f"Expected to find 1 candidate csv for observed flow for global_domain={global_domain}, gage_id={gage_id}, but found {len(candidate_csvs)} when searching from {repr(grandparent)}: {candidate_csvs}"
        )
    obs_dir = os.path.dirname(candidate_csvs[0])
    return obs_dir
