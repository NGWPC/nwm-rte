from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import os
import re
from typing import Literal

# from mswm.utils.settings import LAGGED_ENSEMBLE_MEMBER_LAGS
# TODO replace with import of mswm.utils.settings.LAGGED_ENSEMBLE_MEMBER_LAGS
from consts import LAGGED_ENSEMBLE_MEMBER_LAGS

from mswm.utils.input_configuration import (
    InputConfig,
    GeneralConfig,
    ModulePropertiesConfig,
    ForcingConfig,
    DataFileConfig,
    NWMOutputConfig,
    ParallelConfig,
)
from mswm.utils import settings as mswm_settings
from mswm.utils.settings import DEFAULT_DATETIME_FORMAT as DDF

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from pydantic.dataclasses import dataclass as pydantic_dataclass

import consts as c
from utils import make_wcoss_path_symlinks, booleanize


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


@pydantic_dataclass
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

        pattern = "^[a-z][a-z0-9-\,]*[a-z]$"
        if not re.fullmatch(pattern, self.models_csv):
            raise ValueError(
                f"Expected models to match pattern {repr(pattern)} but got: {repr(self.models_csv)}"
            )
        self.cfe_aet_rootzone = booleanize(self.cfe_aet_rootzone)


def build_model_formulations_for_test(
    model_formulations_file: str | None = None,
) -> list[ModelFormulation]:
    """If model_formulations_file is provided, then parse it to return a list of ModelFormulation instance.
    Otherwise, return a list of length 1 using consts.DEFAULT_MODEL_FORMULATION_ARGS"""
    model_formulations = []

    if model_formulations_file is None:
        model_formulations.append(ModelFormulation(*c.DEFAULT_MODEL_FORMULATION_ARGS))
    else:
        print(f"Reading: {model_formulations_file}")
        if not model_formulations_file.endswith(".tsv"):
            raise ValueError(
                f"Expected model_formulations_file to end with .tsv (indicating tab-separated values) but received: {model_formulations_file}"
            )
        df = pd.read_csv(model_formulations_file, sep="\t")
        for i, row in df.iterrows():
            formulation_csv = row["formulation_mswm"]
            rz_raw = row["uses_root_zone"]
            if str(rz_raw).lower().strip() in ("true", "1", "yes"):
                rz = True
            elif str(rz_raw).lower().strip() in ("false", "0", "no"):
                rz = False
            else:
                raise ValueError(
                    f"Unexpected value for uses_root_zone of row {i} of file {model_formulations_file}: {row}"
                )

            # # NOTE for testing a small batch
            # if len(model_formulations) > 2:
            #     break
            # if rz is not True:
            #     continue

            model_formulations.append(ModelFormulation(formulation_csv, rz))

    return model_formulations


class RTEBaseConfig(BaseModel):
    """Base RTE configuration class to be inherited by child classes.
    Triggers certain setup actions, such as creation of WCOSS-path symlinks.
    Classes that inherit from this should call super().model_post_init(__context) inside their own
    model_post_init() method, if they have that method also defined in the child."""

    # Set during init
    delete_scratch_and_mesh_first: bool
    delete_forcing_raw_input_first: bool
    nprocs: int = Field(ge=1)
    global_domain: str
    forcing_static_dir: str
    forcing_provider: str
    model_formulation_cli_csv: str | None = Field(default=None)
    model_formulation_cli_rootzone: str | None = Field(default=None)
    add_timestamp_to_run_name: bool
    nwm_output_vars: bool = Field(default=False)
    """Passed to MSWM NWMOutputConfig. Does not apply to calibration workflow."""

    # Set after init (not provided as args)
    errors: list | None = Field(init=False, default=None)

    gage_id: str = Field(init=False, default=None)
    gage_vintage: str = Field(init=False, default=None)

    # For lagged ensemble
    use_lagged_ensemble: bool | None = Field(init=False, default=False)
    lagged_ens_mem: str | None = Field(init=False, default=None)
    forcing_lag: str | None = Field(init=False, default=None)
    le__open_loop_state: str | None = Field(init=False, default=None)
    le__closed_loop_state: str | None = Field(init=False, default=None)
    # For model formulation
    model_formulation: ModelFormulation | None = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        self.errors = []
        make_wcoss_path_symlinks()
        self._parse_model_formulation_args()

    def _parse_gage_id__gage_vintage(self) -> None:
        """Parse the provided string and split it into two strings: gage_id and gage_vintage and set attributes.
        Extend errors list as appropriate.
        Called by child classes which define the necessary attributes."""
        gage_id, gage_vintage = self.gage_id__gage_vintage

        if gage_id != gage_id.strip():
            self.errors.append(
                ValueError(f"Whitespace found on end of gage_id: {repr(gage_id)}")
            )
            gage_id = None

        if gage_vintage != gage_vintage.strip():
            self.errors.append(
                ValueError(
                    f"Whitespace found on end of gage_vintage: {repr(gage_vintage)}"
                )
            )
            gage_vintage = None

        self.gage_id = gage_id
        self.gage_vintage = gage_vintage

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

    def _parse_model_formulation_args(self):
        """Break up the multipart model formulation arg into distinct args and set them."""
        self.model_formulation = ModelFormulation(
            self.model_formulation_cli_csv,
            self.model_formulation_cli_rootzone,
        )

    def _add_ts_to_run_name(self):
        if self.add_timestamp_to_run_name:
            if not self.fcst_run_name:
                raise ValueError(
                    "Must provide fcst_run_name when using timestamp_run_name"
                )
            now = datetime.now(tz=timezone.utc)
            self.fcst_run_name = f"{self.fcst_run_name}_{now.strftime(c.RUN_NAME_TIMESTAMP_SUFFIX_FORMAT)}"


class RTEDefaultConfig(RTEBaseConfig):
    """Configuration class for building and running one default realization
    (realtime forcing configuration or historical / retrospective forcing configuration).

    Attributes
    ----------
    delete_scratch_and_mesh_first: bool
        Causes scratch dir and intermediary mesh to be deleted first
    delete_forcing_raw_input_first: bool
        Causes realtime forcing data cache dir to be deleted first
    gage_id__gage_vintage: list[str] = Field(min_length=2, max_length=2)
        Gage ID and vintage
    global_domain: str
        e.g. "CONUS", "Hawaii", "Alaska", "PuertoRico"
    forcing_static_dir :
        Forcing static directory
    forcing_provider: str
        Forcing provider, i.e. "bmi" or "csv"
    cycle_datetime: datetime
        Start time of the realization
    historical_sim_duration: timedelta | None
        Duration of the simulation (only used for historical / retrospective forcing configurations)
    forcing_configuration: str
        Forcing configuration, e.g. "aorc" or "short_range"
    fcst_run_name: str
        Name of the forecast realization run. Affects a directory name.
    nprocs: int = Field(ge=1)
        Number of processors to use
    # The following are set after init during self.model_post_init(). Do not provide
    gage_id: str = Field(init=False, default=None)
        Gage ID
    gage_vintage: str = Field(init=False, default=None)
        Gage vintage
    realtime_mode: bool = Field(init=False, default=None)
        Realtime mode
    realization_builder_kwargs: dict = Field(init=False, default=None)
        Realization builder kwargs (passed to `nwm-msw-mgr`)
    """

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    gage_id__gage_vintage: list[str] = Field(min_length=2, max_length=2)
    cycle_datetime: datetime
    historical_sim_duration: timedelta | None
    forcing_configuration: str
    fcst_run_name: str
    # For medium-range lagged ensemble
    lagged_ensemble_args: list[str] | None = Field(min_length=3, max_length=3)

    # Set after init
    realtime_mode: bool = Field(init=False, default=None)

    # Other derived attrs (not passed to __init__)
    realization_builder_kwargs: dict = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTEBaseConfig's post init
        super()._parse_gage_id__gage_vintage()
        super()._add_ts_to_run_name()

        if (
            self.forcing_configuration
            not in c.FORECAST_FORCING_CONFIGURATION_TYPES__ALL + ["medium_range"]
        ):
            self.realtime_mode = False
        else:
            self.realtime_mode = True

        if (not self.realtime_mode) and (not self.historical_sim_duration):
            self.errors.extend(
                [
                    f"Forcing configuration {repr(self.forcing_configuration)} is *not* realtime, and requires that CLI arg -dur aka --historical_sim_duration is provided, but it was not."
                ]
            )
        if self.realtime_mode and self.historical_sim_duration:
            self.errors.extend(
                [
                    f"Forcing configuration {repr(self.forcing_configuration)} *is* realtime, but CLI arg -dur aka --historical_sim_duration was also provided (it should not be)."
                ]
            )

        super()._parse_lagged_ensemble_args()
        self.realization_builder_kwargs = self._make_realization_builder_kwargs()
        if self.errors:
            raise RuntimeError(self.errors)

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

        obs_dir, nwmretro_file, errors = get_data_paths_for_lstm(
            self.global_domain,
            self.gage_id,
            models_csv=self.model_formulation.models_csv,
        )
        if errors:
            raise RuntimeError(errors)

        realization_kwargs = {
            # "input_path": forecast_vars.forecast_input_config,
            "fcst_run_name": self.fcst_run_name,
            "config_overrides": InputConfig(
                General=GeneralConfig(
                    basin=self.gage_id,
                    run_type="default",
                    models=self.model_formulation.models_csv,
                    formulation=fpp.formulation_name,
                    main_dir=c.DEFAULT_MAIN_DIR,
                    start_period=start_period,
                    end_period=end_period,
                    output_precip=True,
                    output_swe=True,
                    output_sm=True,
                    domain=self.global_domain.lower(),
                ),
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
                    forcing_product_versions=c.FORCING_PRODUCT_VERSIONS_DICT,
                ),
                NWMOutput=NWMOutputConfig(nwm_output_variables=self.nwm_output_vars),
                DataFile=DataFileConfig(
                    **(
                        c.DATAFILE_LIBS
                        | {
                            "obs_dir": obs_dir,
                            "nwmretro_file": nwmretro_file,
                            "hydrofab_file": f"{c.HYDROFABRIC_DIR}/2.2/{self.global_domain}/{self.gage_id}/GEOPACKAGE/USGS/{self.gage_vintage}/gauge_{self.gage_id}.gpkg",
                        }
                    ),
                ),
                Parallel=make_parallel_config(self.nprocs),
                ModuleProperties=ModulePropertiesConfig(
                    cfe_aet_rootzone=self.model_formulation.cfe_aet_rootzone,
                ),
            ),
            # Lagged ensemble args
            "use_lagged_ens": self.use_lagged_ensemble,
            "lagged_ens_mem": self.lagged_ens_mem,
            "forcing_lag": self.forcing_lag,
        }
        return realization_kwargs


class RTECalibConfig(RTEBaseConfig):
    """Configuration class for building and running one calibration realization.

    Attributes
    ----------
    delete_scratch_and_mesh_first: bool
        Causes scratch dir and intermediary mesh to be deleted first
    delete_forcing_raw_input_first: bool
        Causes realtime forcing data cache dir to be deleted first
    objective_function: c.CalObjective
        Objective function, e.g. "kge"
    optimization_algorithm: c.CalOptimizationAlgo
        Optimization algorithm, e.g. "dds"
    nprocs: int = Field(ge=1)
        Number of processors to use
    gage_id__gage_vintage: list[str] = Field(min_length=2, max_length=2)
        Gage ID and vintage
    calib_sim_start: datetime
        Calibration start time
    calib_sim_duration: timedelta
        Calibration simulation duration
    calib_eval_delayment: timedelta
        Used for evaluation / validation time windowing
    valid_sim_advancement: timedelta
        Used for evaluation / validation time windowing
    valid_eval_curtailment: timedelta
        Used for evaluation / validation time windowing
    forcing_source: str
        Source of forcing data, e.g. "aorc" or "nwm"
    global_domain: str
        e.g. "CONUS", "Hawaii", "Alaska", "PuertoRico"
    forcing_provider: str
        Forcing provider, i.e. "bmi" or "csv"
    forcing_static_dir: str
        Forcing static directory
    worker_name: str | None
        Name of the ngen worker (used to build a directory name)
    # The following are set after init during self.model_post_init(). Do not provide.
    gage_id: str = Field(init=False, default=None)
        Gage ID
    gage_vintage: str = Field(init=False, default=None)
        Gage vintage
    obs_dir: str | None = Field(init=False, default=None)
        Directory of observed flow data
    nwmretro_file: str | None = Field(init=False, default=None)
        File containing retrospective NWM flow data
    """

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    objective_function: c.CalObjective
    optimization_algorithm: c.CalOptimizationAlgo
    gage_id__gage_vintage: list[str] = Field(min_length=2, max_length=2)
    calib_sim_start: datetime
    calib_sim_duration: timedelta
    calib_eval_delayment: timedelta
    valid_sim_advancement: timedelta
    valid_eval_curtailment: timedelta
    forcing_source: str
    worker_name: str | None

    # Set after init
    obs_dir: str | None = Field(init=False, default=None)
    nwmretro_file: str | None = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTEBaseConfig's post init
        super()._parse_gage_id__gage_vintage()

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
    delete_scratch_and_mesh_first: bool
        Causes scratch dir and intermediary mesh to be deleted first
    delete_forcing_raw_input_first: bool
        Causes realtime forcing data cache dir to be deleted first
    objective_function: c.CalObjective
        Affects input realization path. Objective function of previously-ran calibration realization, e.g. "kge"
    optimization_algorithm: c.CalOptimizationAlgo
        Affects input realization path. Optimization algorithm of previously-ran calibration realization, e.g. "dds"
    gage_id: str
        Gage ID
    global_domain: str
        e.g. "CONUS", "Hawaii", "Alaska", "PuertoRico"
    forcing_static_dir: str
        Forcing static directory
    forcing_provider: str
        Forcing provider, i.e. "bmi" or "csv"
    cycle_datetime: datetime | None
        Start time of the realization (or end time for coldstart, if `cold_start_datetime` is provided)
    cold_start_datetime: datetime | None
        Start time of the coldstart realization. If None, coldstart is not performed.
    forcing_configuration: str
        Forcing configuration, e.g. "aorc" or "short_range"
    fcst_run_name: str
        Name of the forecast realization run
    nprocs: int = Field(ge=1)
        Number of processors to use
    # The following are set after init during self.model_post_init(). Do not provide.
    run_dir_base: str = Field(init=False, default=None)
        Run directory root
    run_dir_input: str = Field(init=False, default=None)
        Input run directory
    run_dir_output: str = Field(init=False, default=None)
        Output run directory
    ngen_log_file: str = Field(init=False, default=None)
        ngen stdout + stderr stream log file
    valid_best_yaml: str = Field(init=False, default=None)
        Validation yaml file (output from previously-ran calibration realization)
    realization_builder_kwargs: dict = Field(init=False, default=None)
        Realization builder kwargs (passed to `nwm-msw-mgr`)
    """

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    ### These calibration parameters affect directory path
    objective_function: c.CalObjective
    optimization_algorithm: c.CalOptimizationAlgo
    gage_id: str
    cycle_datetime: datetime | None
    cold_start_datetime: datetime | None
    forcing_configuration: str
    fcst_run_name: str
    # For medium-range lagged ensemble
    lagged_ensemble_args: list[str] | None = Field(min_length=3, max_length=3)

    # Derived paths (not passed to __init__)
    run_dir_base: str = Field(init=False, default=None)
    run_dir_input: str = Field(init=False, default=None)
    run_dir_output: str = Field(init=False, default=None)
    ngen_log_file: str = Field(init=False, default=None)
    valid_best_yaml: str = Field(init=False, default=None)

    # Other derived attrs (not passed to __init__)
    realization_builder_kwargs: dict = Field(init=False, default=None)

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTEBaseConfig's post init
        super()._add_ts_to_run_name()

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
                    forcing_product_versions=c.FORCING_PRODUCT_VERSIONS_DICT,
                ),
                NWMOutput=NWMOutputConfig(nwm_output_variables=self.nwm_output_vars),
                Parallel=make_parallel_config(self.nprocs),
                ModuleProperties=ModulePropertiesConfig(
                    cfe_aet_rootzone=self.model_formulation.cfe_aet_rootzone,
                ),
            ),
            # Lagged ensemble args
            "use_lagged_ens": self.use_lagged_ensemble,
            "lagged_ens_mem": self.lagged_ens_mem,
            "forcing_lag": self.forcing_lag,
        }
        self.realization_builder_kwargs = realization_kwargs


class RTETestConfig(RTEBaseConfig):
    """Configuration class for building and running a set of test realizations.

    Attributes
    ----------
    delete_scratch_and_mesh_first: bool
        Causes scratch dir and intermediary mesh to be deleted first
    delete_forcing_raw_input_first: bool
        Causes realtime forcing data cache dir to be deleted first
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
    do_all_optimization_algorithms: bool
        For calibration, causes all optimization algorithms to be used.
    do_all_forcing_configs: bool
        Causes all forcing configurations to be used, e.g. "short_range", "standard_ana", "medium_range_blend", "extended_ana", "short_range_hawaii", etc.
    do_coldstart: bool
        Causes coldstart to be ran before forecast.
    fcst_run_name: str
        Name of the forecast realization run. Affects a directory name.
    nprocs: int = Field(ge=1)
        Number of processors to use
    gage_id__gage_vintage: list[str] = Field(min_length=2, max_length=2)
        Gage ID and vintage
    global_domain: str
        e.g. "CONUS", "Hawaii", "Alaska", "PuertoRico"
    forcing_provider: str
        Forcing provider, i.e. "bmi" or "csv"
    forcing_static_dir: str
        Forcing static directory
    noop: bool
        Causes a noop to occur (for confirming that Python packages are importable).
    gage_id: str = Field(init=False, default=None)
        Gage ID
    gage_vintage: str = Field(init=False, default=None)
        Gage vintage
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
    gage_id__gage_vintage: list[str] = Field(min_length=2, max_length=2)
    noop: bool
    restart: bool

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)  # Call RTEBaseConfig's post init
        super()._parse_gage_id__gage_vintage()
        super()._add_ts_to_run_name()

        if self.quit_forecast_after_forcing_running:
            self.errors.append(
                RuntimeError(
                    "quit_forecast_after_forcing_running is currently not allowed, pending updates."
                )
            )

        errors_extend = parse_fcst_run_name(self.fcst_run_name)
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
    models_csv: str,
) -> tuple[str | None, str | None, list[Exception]]:
    """Build and return two data paths needed for LSTM model,
    as well as a list of errors encountered during this function.
    Return None for obs_dir and nwmretro_file if not LSTM."""

    errors: list[Exception] = []

    if "lstm" in models_csv.lower():
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
