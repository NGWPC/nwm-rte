"""Primary configuration classes. Pydantic BaseModels directly associated with CLI executables."""

import os
from datetime import datetime, timedelta, timezone

from mswm.utils import settings as mswm_settings
from mswm.utils.input_configuration import (
    CalibConfig,
    DataFileConfig,
    ForcingConfig,
    GeneralConfig,
    InputConfig,
    ModulePropertiesConfig,
    NWMOutputConfig,
    ParallelConfig,
)
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT as DDF
from pydantic import BaseModel, ConfigDict, Field

from ngen_rte import consts as c

# from mswm.utils.settings import LAGGED_ENSEMBLE_MEMBER_LAGS
# TODO replace with import of mswm.utils.settings.LAGGED_ENSEMBLE_MEMBER_LAGS
from ngen_rte.consts import LAGGED_ENSEMBLE_MEMBER_LAGS
from ngen_rte.other_classes import (
    CalibTimeWindows,
    ForcingProviderPaths,
    ModelFormulation,
    TestPaths,
)
from ngen_rte.utils import (
    get_paths_for_observed_and_retro_data,
    make_wcoss_path_symlinks,
    parse_fcst_run_name,
)


class RTEBaseConfig(BaseModel):
    """Base RTE configuration class to be inherited by child classes.
    Triggers certain setup actions, such as creation of WCOSS-path symlinks.
    Classes that inherit from this should call super().model_post_init(__context) inside their own
    model_post_init() method, if they have that method also defined in the child.

    The primary usage of this class is to access property mswm_RealizationBuilder_kwargs
    for building (and later running) a realization using MSWM.

    Attributes
    ----------
    delete_scratch_and_mesh_first: bool
        Causes scratch dir and intermediate mesh file to be deleted before building the realization. Use with caution.
    delete_forcing_raw_input_first: bool
        Causes forcing raw input dir to be deleted before building the realization. Use with caution.
    environment: str
        Operating environment, e.g. 'test' or 'oe'.
    nprocs: int = Field(ge=1)
        Number of processors to use for ngen execution.
    global_domain: str
        Global domain, e.g. "CONUS" or "Hawaii". Must agree with the ID of the basin / gage / VPU being simulated.
    forcing_static_dir: str
        Directory for static forcing data.
    gage_id: str
        Gage ID.
    model_formulation_cli_csv: str | None = Field(default=None)
        Comma-separated string of model names comprising the formulation.
    model_formulation_cli_rootzone: str | None = Field(default=None)
        Boolean for model formulation rootzone parameter.
    add_timestamp_to_run_name: bool = Field(default=False)
        Boolean causing the final forecast run name to contain a timestamp suffix.
    nwm_output_vars: bool = Field(default=False)
        Boolean causing NWM output variables to be included in the output. Passed to MSWM NWMOutputConfig. Does not apply to calibration workflow.
    hydrofab_file: str | None = Field(default=None)
        Optional hydrofabric file path. If provided, bypasses MSWM Icefabric server API call.
    fcst_run_name: str | None = Field(default=None)
        Forecast run name.
    cycle_datetime: datetime | None = Field(default=None)
        Cycle datetime for forecast
    """

    # Set during init
    delete_scratch_and_mesh_first: bool
    delete_forcing_raw_input_first: bool
    environment: str
    nprocs: int = Field(ge=1)
    global_domain: str
    forcing_static_dir: str
    gage_id: str
    model_formulation_cli_csv: str | None = Field(default=None)
    model_formulation_cli_rootzone: str | None = Field(default=None)
    add_timestamp_to_run_name: bool = Field(default=False)
    nwm_output_vars: bool = Field(default=False)
    hydrofab_file: str | None = Field(default=None)
    fcst_run_name: str | None = Field(default=None)
    cycle_datetime: datetime | None = Field(default=None)

    # Set after init (not provided as args)
    time_at_init: datetime | None = Field(init=False, default=None)
    """Time at class instantiation."""
    errors: list | None = Field(init=False, default=None)
    """List of exceptions encountered during init."""

    # For lagged ensemble.  Used by run_forecast.py and run_default.py.  See CLI args for those scripts and see _parse_lagged_ensemble_args() for details.
    use_lagged_ensemble: bool | None = Field(init=False, default=False)
    """Boolean indicating that lagged ensemble is to be used. Passed to MSWM."""
    lagged_ens_mem: str | None = Field(init=False, default=None)
    """Lagged ensemble member name. Passed to MSWM."""
    forcing_lag: int | None = Field(init=False, default=None)
    """Lagged ensemble forcing lag. Looked up based on lagged ensemble member name. Passed to MSWM."""
    le__open_loop_state: str | None = Field(init=False, default=None)
    """File path for lagged ensemble open loop state."""
    le__closed_loop_state: str | None = Field(init=False, default=None)
    """File path for lagged ensemble closed loop state."""

    def model_post_init(self, __context) -> None:
        self.time_at_init = datetime.now(tz=timezone.utc)
        self.errors = []
        make_wcoss_path_symlinks()
        if self.errors:
            raise RuntimeError(self.errors)

    def _parse_lagged_ensemble_args(self):
        """Break up the multipart lagged ensemble arg into distinct args and set them.
        Called by child classes which define the necessary attributes."""
        if self.lagged_ensemble_args:
            if self.forcing_configuration != "medium_range":
                self.errors.append(
                    ValueError(
                        f"lagged ensemble only supported for medium_range, but forcing configuration {repr(self.forcing_configuration)} was provided"
                    )
                )
                return

            self.use_lagged_ensemble = True

            member_name, open_ls, closed_ls = self.lagged_ensemble_args

            self.lagged_ens_mem = member_name if member_name.strip() else None
            self.forcing_lag = LAGGED_ENSEMBLE_MEMBER_LAGS[self.lagged_ens_mem]
            self.le__open_loop_state = open_ls if open_ls.strip() else None
            self.le__closed_loop_state = closed_ls if closed_ls.strip() else None

            if self.lagged_ens_mem not in LAGGED_ENSEMBLE_MEMBER_LAGS:
                self.errors.append(
                    KeyError(
                        f"Invalid lagged ensemble member {repr(self.lagged_ens_mem)} (choose from: {list(LAGGED_ENSEMBLE_MEMBER_LAGS)})"
                    )
                )

        if self.le__open_loop_state or self.le__closed_loop_state:
            self.errors.append(
                NotImplementedError(
                    "Lagged ensemble args for Open Loop State and Closed Loop State are not yet implemented in nwm-rte (should be provided as empty strings for now)"
                )
            )

    @property
    def _fcst_run_name_formatted(self) -> str:
        """Adaptive forecast run name that optionally can have a timestamped suffix appended to the end."""
        if self.add_timestamp_to_run_name:
            if not self.fcst_run_name:
                raise ValueError(
                    "Must provide fcst_run_name when using timestamp_run_name"
                )
            return f"{self.fcst_run_name}_{self.time_at_init.strftime(c.RUN_NAME_TIMESTAMP_SUFFIX_FORMAT)}"
        else:
            return f"{self.fcst_run_name}"

    @property
    def realtime_mode(self) -> bool:
        """Realtime mode boolean, leveraged by default realization which can run both realtime and historical/retrospective configurations."""
        if self.forcing_configuration in c.FORECAST_FORCING_TYPES + ["medium_range"]:
            return True
        else:
            return False

    @property
    def forcing_provider_paths(self) -> ForcingProviderPaths:
        """Helper class for managing forcing provider paths."""
        fpp = ForcingProviderPaths(
            global_domain=self.global_domain,
            forcing_static_dir=self.forcing_static_dir,
        )
        return fpp

    @property
    def calib_windows(self) -> CalibTimeWindows:
        """Class of various calibration time windows."""
        windows = CalibTimeWindows(
            calib_sim_start=self.calib_sim_start
            if self.calib_sim_start
            else c.CALIB_SIM_START_DEFAULT,
            calib_sim_duration=self.duration
            if self.duration
            else c.CALIB_SIM_DURATION_DEFAULT,
            calib_eval_delayment=c.CALIB_EVAL_DELAYMENT_DEFAULT,
            valid_sim_advancement=c.VALID_SIM_ADVANCEMENT_DEFAULT,
            valid_eval_curtailment=c.VALID_EVAL_CURTAILMENT_DEFAULT,
        )
        return windows

    @property
    def start_period__end_period(self) -> tuple[str | None, str | None]:
        """Tuple of start period and end period for calibration and default realizations."""
        if isinstance(self, RTECalibConfig):
            start_period = self.calib_windows.calib_eval_start.strftime(DDF)
            end_period = self.calib_windows.calib_eval_end.strftime(DDF)
        elif isinstance(self, RTEDefaultConfig) and not self.realtime_mode:
            start_period = self.cycle_datetime.strftime(DDF)
            end_period = (self.cycle_datetime + self.duration).strftime(DDF)
        else:
            start_period = None
            end_period = None
        return start_period, end_period

    @property
    def model_formulation(self) -> ModelFormulation:
        """Model formulation helper class for MSWM models list and rootzone parameter."""
        mf = ModelFormulation(
            self.model_formulation_cli_csv,
            self.model_formulation_cli_rootzone,
        )
        return mf

    @property
    def run_type(self) -> str:
        """Run type for MSWM GeneralConfig"""
        if isinstance(self, RTECalibConfig):
            rt = "calibration"
        elif isinstance(self, RTEDefaultConfig):
            rt = "default"
        elif isinstance(self, RTEForecastConfig):
            rt = "default"
        else:
            raise ValueError(
                f"Unexpected config class {type(self)}. Expected one of RTEForecastConfig, RTECalibConfig, or RTEDefaultConfig."
            )
        return rt

    @property
    def mswm_GeneralConfig(self) -> GeneralConfig:
        """MSWM GeneralConfig instance"""
        start_period, end_period = self.start_period__end_period
        return GeneralConfig(
            basin=self.gage_id,
            environment=self.environment,
            run_type=self.run_type,
            models=self.model_formulation.models_csv,
            formulation=self.forcing_provider_paths.formulation_name,
            main_dir=c.DEFAULT_MAIN_DIR,
            start_period=start_period,
            end_period=end_period,
            output_precip=True,
            output_swe=True,
            output_sm=True,
            domain=self.global_domain.lower(),
        )

    @property
    def mswm_ModulePropertiesConfig(self) -> ModulePropertiesConfig:
        """MSWM ModulePropertiesConfig instance"""
        mpc = ModulePropertiesConfig(
            cfe_aet_rootzone=self.model_formulation.cfe_aet_rootzone,
        )
        return mpc

    @property
    def mswm_NWMOutputConfig(self) -> NWMOutputConfig:
        """MSWM NWMOutputConfig instance"""
        oc = NWMOutputConfig(nwm_output_variables=self.nwm_output_vars)
        return oc

    @property
    def mswm_RegionalizationConfig(self) -> None:
        """MSWM RegionalizationConfig instance"""
        return None

    @property
    def mswm_CalibConfig(self) -> CalibConfig | None:
        """MSWM CalibConfig instance"""
        if not isinstance(self, RTECalibConfig):
            return None
        cc = CalibConfig(
            optimization_algorithm=self.optimization_algorithm,
            swarm_size=c.CALIB_SWARM_SIZE,
            c1=c.CALIB_PSO_C1,
            c2=c.CALIB_PSO_C2,
            w=c.CALIB_PSO_W,
            objective_function=self.objective_function,
            start_iteration=c.CALIB_ITER_START,
            number_iteration=c.CALIB_ITER_COUNT,
            calib_output_vars=True,
            valid_output_vars=True,
            calib_start_period=self.calib_windows.calib_sim_start.strftime(DDF),
            calib_end_period=self.calib_windows.calib_sim_end.strftime(DDF),
            calib_eval_start_period=self.calib_windows.calib_eval_start.strftime(DDF),
            calib_eval_end_period=self.calib_windows.calib_eval_end.strftime(DDF),
            valid_start_period=self.calib_windows.valid_sim_start.strftime(DDF),
            valid_end_period=self.calib_windows.valid_sim_end.strftime(DDF),
            valid_eval_start_period=self.calib_windows.valid_eval_start.strftime(DDF),
            valid_eval_end_period=self.calib_windows.valid_eval_end.strftime(DDF),
            full_eval_start_period=self.calib_windows.full_eval_start.strftime(DDF),
            full_eval_end_period=self.calib_windows.full_eval_end.strftime(DDF),
            save_plot_iter_freq=c.CALIB_SAVE_PLOT_ITER_FREQ,
            ngen_cerf=False,
            calib_parameter_file=c.CALIB_PARAMETERS_DIR,
        )
        return cc

    @property
    def mswm_ForcingConfig(self) -> ForcingConfig:
        """MSWM ForcingConfig instance.
        Contains dynamic logic for handling different types of child classes of RTEBaseConfig."""
        if isinstance(self, RTECalibConfig):
            cdt = self.calib_windows.calib_sim_start.strftime(
                mswm_settings.DEFAULT_DATETIME_FORMAT
            )
        elif isinstance(self, (RTEForecastConfig, RTEDefaultConfig)):
            cdt = (
                self.cycle_datetime.strftime(mswm_settings.DEFAULT_DATETIME_FORMAT)
                if self.cycle_datetime
                else None
            )
        else:
            raise ValueError(
                f"Unexpected config class {type(self)}. Expected one of RTEForecastConfig, RTECalibConfig, or RTEDefaultConfig."
            )
        cold_start_datetime = (
            self.cold_start_datetime.strftime(mswm_settings.DEFAULT_DATETIME_FORMAT)
            if isinstance(self, RTEForecastConfig) and self.cold_start_datetime
            else None
        )
        fc = ForcingConfig(
            forcing_provider=c.FORCING_PROVIDER,
            forcing_dir=self.forcing_static_dir,
            forcing_template_dir=c.FORCING_TEMPLATE_DIR,
            root_dir=c.FORCING_ROOT_DIR,
            forcing_configuration=self.forcing_configuration,
            cycle_datetime=cdt,
            cold_start_datetime=cold_start_datetime,
            forcing_static_dir=self.forcing_static_dir,
            scratch_dir_override=c.SCRATCH_DIR_OVERRIDE,
            forcing_product_versions=c.FORCING_PRODUCT_VERSIONS_DICT,
        )
        return fc

    @property
    def mswm_DataFileConfig(self) -> DataFileConfig:
        """MSWM DataFileConfig instance."""
        obs_dir, nwmretro_file, errors = get_paths_for_observed_and_retro_data(
            self.global_domain,
            self.gage_id,
            models_csv=self.model_formulation.models_csv,
        )
        if errors:
            raise RuntimeError(errors)
        dfc = DataFileConfig(
            **(
                c.DATAFILE_LIBS
                | {
                    "obs_dir": obs_dir,
                    "nwmretro_file": nwmretro_file,
                    "hydrofab_file": self.hydrofab_file,
                }
            )
        )
        return dfc

    @property
    def mswm_ParallelConfig(self) -> ParallelConfig:
        """MSWM ParallelConfig instance."""
        pc = make_parallel_config(self.nprocs)
        return pc

    @property
    def mswm_InputConfig(self) -> InputConfig:
        """MSWM InputConfig instance. This is the composite MSWM class that contains the other sub-config classes."""
        general = self.mswm_GeneralConfig
        module_properties = self.mswm_ModulePropertiesConfig
        nwm_output = self.mswm_NWMOutputConfig
        regionalization = self.mswm_RegionalizationConfig
        calibration = self.mswm_CalibConfig
        forcing = self.mswm_ForcingConfig
        data_file = self.mswm_DataFileConfig
        parallel = self.mswm_ParallelConfig
        ic = InputConfig(
            General=general,
            ModuleProperties=module_properties,
            NWMOutput=nwm_output,
            Regionalization=regionalization,
            Calibration=calibration,
            Forcing=forcing,
            DataFile=data_file,
            Parallel=parallel,
        )
        return ic

    @property
    def mswm_RealizationBuilder_kwargs(self) -> dict:
        """Full set of kwargs that are passed to MSWM RealizationBuilder's constructor for bulding a realization."""
        kwargs = {
            # "input_path": forecast_vars.forecast_input_config,
            "valid_yaml": self.valid_best_yaml,
            "fcst_run_name": self._fcst_run_name_formatted,
            "config_overrides": self.mswm_InputConfig,
            "use_lagged_ens": self.use_lagged_ensemble,
            "lagged_ens_mem": self.lagged_ens_mem,
            "forcing_lag": self.forcing_lag,
        }
        if self.errors:
            raise RuntimeError(self.errors)
        return kwargs

    @property
    def run_dir_base(self) -> str:
        """Run directory root"""
        ret = f"{c.DEFAULT_MAIN_DIR}/{self.objective_function.value}_{self.optimization_algorithm.value}/test_{c.FORCING_PROVIDER}/{self.gage_id}"
        if not os.path.isdir(ret):
            msg = f"Not a directory: {repr(ret)}. Please review choices for objective function, optimization algorithm, and gage, which affect this path."
            raise NotADirectoryError(msg)
        return ret

    @property
    def run_dir_input(self) -> str:
        """Input run directory"""
        return f"{self.run_dir_base}/Input"

    @property
    def run_dir_output(self) -> str:
        """Output run directory"""
        return f"{self.run_dir_base}/Output"

    @property
    def ngen_log_file(self) -> str:
        """ngen stdout + stderr stream log file"""
        return f"{self.run_dir_base}/logs/ngen.log"

    @property
    def valid_best_yaml(self) -> str:
        """Validation yaml file (output from previously-ran calibration realization)"""
        return (
            f"{self.run_dir_output}/Validation_Run/{self.gage_id}_config_valid_best.yaml"
            if isinstance(self, RTEForecastConfig)
            else None
        )


class RTEDefaultConfig(RTEBaseConfig):
    """Configuration class for building and running one default realization
    (realtime forcing configuration or historical / retrospective forcing configuration).

    Attributes
    ----------
    cycle_datetime: datetime
        Start time of the realization
    duration: timedelta | None
        Duration of the simulation (only used for historical / retrospective forcing configurations)
    forcing_configuration: str
        Forcing configuration, e.g. "aorc" or "short_range"
    fcst_run_name: str
        Name of the forecast realization run. Affects a directory name.
    lagged_ensemble_args: list[str] | None = Field(min_length=3, max_length=3)
        See CLI help menu for [`run_default.py`](python_cli_help__run_default.py.txt) for details.
    """

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    cycle_datetime: datetime
    duration: timedelta | None
    forcing_configuration: str
    fcst_run_name: str
    # For medium-range lagged ensemble
    lagged_ensemble_args: list[str] | None = Field(min_length=3, max_length=3)

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTEBaseConfig's post init
        super()._parse_lagged_ensemble_args()
        if self.errors:
            raise RuntimeError(self.errors)


class RTECalibConfig(RTEBaseConfig):
    """Configuration class for building and running one calibration realization.

    Attributes
    ----------
    objective_function: c.CalObjective
        Objective function, e.g. "kge"
    optimization_algorithm: c.CalOptimizationAlgo
        Optimization algorithm, e.g. "dds"
    calib_sim_start: datetime
        Calibration start time
    duration: timedelta
        Calibration simulation duration
    calib_eval_delayment: timedelta
        Used for evaluation / validation time windowing
    valid_sim_advancement: timedelta
        Used for evaluation / validation time windowing
    valid_eval_curtailment: timedelta
        Used for evaluation / validation time windowing
    forcing_configuration: str
        Source of forcing data, e.g. "aorc" or "nwm"
    worker_name: str | None
        Name of the ngen worker (used to build a directory name)
    """

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    objective_function: c.CalObjective
    optimization_algorithm: c.CalOptimizationAlgo
    calib_sim_start: datetime
    duration: timedelta
    calib_eval_delayment: timedelta
    valid_sim_advancement: timedelta
    valid_eval_curtailment: timedelta
    forcing_configuration: str
    worker_name: str | None

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTEBaseConfig's post init
        if self.forcing_configuration not in c.CALIB_FORCING_TYPES:
            self.errors.append(
                ValueError(
                    f"Unexpected forcing_configuration: {self.forcing_configuration} (for calibration, choose from: {c.CALIB_FORCING_TYPES})"
                )
            )

        if self.nwm_output_vars:
            self.errors.append(
                ValueError("nwm_output_vars not supported for calibration workflow.")
            )

        if self.errors:
            raise RuntimeError(self.errors)


class RTEForecastConfig(RTEBaseConfig):
    """Configuration class for building and running one forecast realization.

    Attributes
    ----------
    objective_function: c.CalObjective
        Affects input realization path. Objective function of previously-ran calibration realization, e.g. "kge"
    optimization_algorithm: c.CalOptimizationAlgo
        Affects input realization path. Optimization algorithm of previously-ran calibration realization, e.g. "dds"
    cycle_datetime: datetime | None
        Start time of the realization (or end time for coldstart, if `cold_start_datetime` is provided)
    cold_start_datetime: datetime | None
        Start time of the coldstart realization. If None, coldstart is not performed.
    forcing_configuration: str
        Forcing configuration, e.g. "aorc" or "short_range"
    fcst_run_name: str
        Name of the forecast realization run
    lagged_ensemble_args: list[str] | None = Field(min_length=3, max_length=3)
        See CLI help menu for [`run_forecast.py`](python_cli_help__run_forecast.py.txt) for details.
    """

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    # These calibration parameters affect directory path
    objective_function: c.CalObjective
    optimization_algorithm: c.CalOptimizationAlgo
    cycle_datetime: datetime | None
    cold_start_datetime: datetime | None
    forcing_configuration: str
    fcst_run_name: str
    # For medium-range lagged ensemble
    lagged_ensemble_args: list[str] | None = Field(min_length=3, max_length=3)

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTEBaseConfig's post init
        super()._parse_lagged_ensemble_args()
        self._check_time_config()
        if self.errors:
            raise RuntimeError(self.errors)

    def _check_time_config(self) -> None:
        """Validate the configuration"""
        if not (self.cold_start_datetime or self.cycle_datetime):
            self.errors.append(
                ValueError(
                    "Must provide cold_start_datetime or cycle_datetime (or both), but neither were provided."
                )
            )


class RTETestConfig(RTEBaseConfig):
    """Configuration class for building and running a set of test realizations.

    Attributes
    ----------
    skip_forecast: bool
        Causes forecast to be skipped (only do calibration)
    quit_forecast_after_forcing_running: bool
        Causes forecasts to be stopped midway once log files indicate that the model is well underway
    quit_forecast_after_duration: float | None = Field(ge=0)
        Causes forecasts to be stopped midway after a set duration (seconds of processing time)
    do_calibration: bool
        Causes calibration to be ran, before forecasts (needed if a calibration has not yet been ran for the gage)
    quit_calibration_after_duration: float | None = Field(ge=0)
        Causes calibrations to be stopped midway after a set duration (seconds of processing time)
    objective_functions: list[c.CalObjective]
        For calibration, list of objective functions to run, e.g. "kge". Replaced with full list when do_all_objective_functions = True
    do_all_objective_functions: bool
        For calibration, causes all objective functions to be used.
    optimization_algorithms: list[c.CalOptimizationAlgo]
        For calibration, list of optimization algorithms to run, e.g. "dds". Replaced with full list when do_all_optimization_algorithms = True
    model_formulations_file: str | None
        File containing model formulations to iterate over
    calibration_forcing_sources: list[str]
        Calibration forcing configurations, e.g. "aorc" "nwm"
    do_all_optimization_algorithms: bool
        For calibration, causes all optimization algorithms to be used.
    do_all_forcing_configs: bool
        Causes all forcing configurations to be used, e.g. "short_range", "standard_ana", "medium_range_blend", "extended_ana", "short_range_hawaii", etc.
    do_coldstart: bool
        Causes coldstart to be ran before forecast.
    fcst_run_name: str
        Name of the forecast realization run. Affects a directory name.
    noop: bool
        Causes a noop to occur (for confirming that Python packages are importable).
    restart: bool
        Causes the test to be restarted by reading the existing c.TEST_RESULTS_FILE and skipping configurations which had completed earlier. Can be used when long-running tests are interrupted. Use with caution.
    """

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

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
    model_formulations_file: str | None
    calibration_forcing_sources: list[str]
    do_all_optimization_algorithms: bool
    do_all_forcing_configs: bool
    do_coldstart: bool
    fcst_run_name: str
    noop: bool
    restart: bool

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTEBaseConfig's post init

        if self.quit_forecast_after_forcing_running:
            self.errors.append(
                RuntimeError(
                    "quit_forecast_after_forcing_running is currently not allowed, pending updates."
                )
            )

        errors_extend = parse_fcst_run_name(self._fcst_run_name_formatted)
        self.errors.extend(errors_extend)

        if self.do_all_objective_functions:
            self.objective_functions = list(c.CalObjective)
        if self.do_all_optimization_algorithms:
            self.optimization_algorithms = list(c.CalOptimizationAlgo)

        if self.do_all_forcing_configs:
            if self.skip_forecast and (not self.do_coldstart):
                self.errors.append(
                    ValueError(
                        f"When do_all_forcing_configs={self.do_all_forcing_configs}, must have coldstart and/or forecast enabled."
                    )
                )

        if self.errors:
            raise RuntimeError(self.errors)

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
                            obj_func,
                            optim_algo,
                            self.global_domain,
                            self.forcing_static_dir,
                        ),
                    )
                )
        return ret


def make_parallel_config(nprocs: int) -> ParallelConfig:
    """MSWM ParallelConfig instance."""
    if nprocs and nprocs > 1:
        parallel = ParallelConfig(
            parallel_ngen_exe=c.NGEN_BIN__LINK,
            partition_generator_exe=c.PARTITION_GENERATOR_BIN__LINK,
            nprocs=nprocs,
        )
    else:
        parallel = ParallelConfig(nprocs=nprocs)
    return parallel
