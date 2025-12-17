import copy
from dataclasses import dataclass, field
from datetime import datetime
import functools
import os
import shutil
import subprocess
import argparse
from typing import Optional
#import util_deletes
#import util_asserts
#import pprint
#import const 

from mswm.build_inputs import RealizationBuilder
from mswm.utils.input_configuration import (
    InputConfig,
    ForcingConfig,
    valid_configs as mswm_valid_configs,
)
from mswm.utils import settings as mswm_settings

from nwm_fcst_mgr.forecast import run_fcst

from execution_tests import make_parallel_config
import consts as c


print = functools.partial(print, flush=True)

# import logging
# import sys
# logging.basicConfig(
#     level=logging.INFO,
#     handler=logging.StreamHandler(sys.stdout),
#     format="%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(message)s",
# )

@dataclass
class ForecastVars:
    """Configuration object for forecast runs."""
    gage_id: str
    fcst_run_name: str
    formulation_suffix: str
    root_dir: str
    calib_input_config: str
    forecast_input_config: str
    forecast_rounds: int   
    coldstart_start: Optional[str]
    coldstart_end: Optional[str]
    forecast_initial_cycle_datetime: Optional[str]
    forcing_configuration: Optional[str]
    nprocs: int

    # Derived paths (not passed to __init__)
    run_dir_base: str = field(init=False)
    run_dir_input: str = field(init=False)
    run_dir_output: str = field(init=False)
    ngen_log_file: str = field(init=False)
    valid_best_yaml: str = field(init=False)   

    
    def __post_init__(self):
        """Validate configuration and set derived paths."""
        
        #if not self.gage_id:
        #    raise ValueError("gage_id is required")
        #if not self.forecast_initial_cycle_datetime:
        #    raise ValueError("forecast_initial_cycle_datetime is required")
        
        #compute derived paths
        self.run_dir_base = f"{self.root_dir}/run_ngen/test_{self.formulation_suffix}/{self.gage_id}"
        self.run_dir_input = f"{self.run_dir_base}/Input"
        self.run_dir_output = f"{self.run_dir_base}/Output"
        self.ngen_log_file = f"{self.run_dir_base}/logs/ngen.log"
        self.valid_best_yaml = f"{self.run_dir_output}/Validation_Run/{self.gage_id}_config_valid_best.yaml"

# @dataclass
# class SavedStartState_PseudoCode:
#    """Pseudocode"""
#
#    forecast_type: str
#    cycle_datetime: datetime
#    realization_file: str

def set_vars(options) -> ForecastVars:
    """
    Creates a ForecastVars object from parsed command-line options.
    :param options: Namespace object from argparse
    :return: ForecastVars object
    """
    return ForecastVars(
        gage_id=options.gage or c.DEFAULT_GAGE_ID,
        fcst_run_name=options.fcst_run_name or c.DEFAULT_FORECAST_RUN_NAME,
        formulation_suffix=options.forcing_provider or c.DEFAULT_FORCING_PROVIDER,
        coldstart_start=options.cold_start_datetime,
        coldstart_end=options.cycle_datetime if options.cold_start_datetime else None,
        forecast_initial_cycle_datetime=options.cycle_datetime,
        forcing_configuration=options.forcing_configuration or c.FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT[0],
        nprocs=options.nprocs or c.DEFAULT_NPROCS,
        root_dir = "/ngen-app/data",
        calib_input_config = "/ngen-app/data/configs/rte_cal_input_bmi.config",
        forecast_input_config = "/ngen-app/data/configs/forecast_input.config",
        forecast_rounds = 1,
    )

def create_kwargs(forecast_vars) -> dict:
    if forecast_vars.forecast_initial_cycle_datetime:
        cycle_datetime = forecast_vars.forecast_initial_cycle_datetime.strftime(mswm_settings.DEFAULT_DATETIME_FORMAT)
    else:
        cycle_datetime = None
    realization_kwargs = {
        #"input_path": forecast_vars.forecast_input_config,
        "valid_yaml": forecast_vars.valid_best_yaml,
        "fcst_run_name": forecast_vars.fcst_run_name,
        "config_overrides" : InputConfig(
            Forcing=ForcingConfig(
                forcing_provider=forecast_vars.formulation_suffix,
                forcing_dir=None,
                forcing_template_dir="/ngwpc/ngen-forcing/NextGen_Forcings_Engine_BMI/BMI_NextGen_Configs/config_templates/",
                root_dir=forecast_vars.root_dir,
                forcing_configuration=forecast_vars.forcing_configuration,
                cycle_datetime=cycle_datetime,
                cold_start_datetime=None,
            )
        )
    }

    return realization_kwargs


def calibration__build_and_run(forecast_vars) -> None:
    print("Building calibration realization")
    rb_calib = RealizationBuilder(forecast_vars.calib_input_config)
    rb_calib.config_overrides = InputConfig(Parallel=make_parallel_config(nprocs=forecast_vars.nprocs))
    rb_calib.build_calib_realization()
    #assert_paths_common_input()
    if not os.path.isfile(rb_calib.calib_config_file):
        raise FileNotFoundError(rb_calib.calib_config_file)
    print("Running calibration")
    cmd = [
        "python",
        "/ngen-app/bin/calibration.py",
        str(rb_calib.calib_config_file),
    ]
    print(f"Running command args: {cmd}")
    subprocess.check_call(cmd)
    shutil.copyfile(forecast_vars.ngen_log_file, forecast_vars.ngen_log_file + ".calib.log")


def build_coldstart_realization(fcst_kwargs, forecast_vars):
    rb_cs = RealizationBuilder(**fcst_kwargs, use_cold_start=True)
    # This can be called before the overrides (InputConfig instance) is defined, to load the .conf file first without overrides.
    # Then overrides can be idiomatically defined by copying the valid config and replacing individual keys.
    # This can be skipped if defining overrides (InputConfig instance) from scratch without relying on anything from .conf.
    rb_cs.load_config_apply_overrides()

    forcing_config = copy.deepcopy(rb_cs.input_configs["Forcing"])
    cs_overrides_dict = {
        "forcing_configuration": forecast_vars.forcing_configuration,
        "cold_start_datetime": forecast_vars.coldstart_start.strftime(mswm_settings.DEFAULT_DATETIME_FORMAT),
        "cycle_datetime": forecast_vars.coldstart_end.strftime(mswm_settings.DEFAULT_DATETIME_FORMAT),
    }
    forcing_config.update(cs_overrides_dict)
    print(f"Building coldstart realization: {forcing_config}")
    rb_cs.config_overrides = InputConfig(Forcing=ForcingConfig(**forcing_config))
    rb_cs.build_fcst_realization()
    print(f"Wrote: {rb_cs.realization_file}")
    return rb_cs


def build_forecast_realization(fcst_kwargs):
    
    rb_fcst = RealizationBuilder(**fcst_kwargs, use_cold_start=False)
    rb_fcst.build_fcst_realization()
    return rb_fcst
    

def datetime_type(datetime_str):
    return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")


def get_options(args_list=None):
    """
    Parses command-line arguments for configurations.

    :return: Namespace object containing the parsed arguments.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-forcing_provider',
                        type=str,
                        help=f"Forcing provider to use, e.g., 'bmi' or 'csv'. Default: {repr(c.DEFAULT_FORCING_PROVIDER)}")
    parser.add_argument('-cycle_datetime',
                        type=datetime_type,
                        help="start date/time for the forecast cycle (also the end of cold-start if chosen), format= 'YYYY-MM-DD HH:mm:ss'. If omitted, a forecast will not be ran.")
    parser.add_argument('-cold_start_datetime',
                        type=datetime_type,
                        help="start date/time for cold-start, format= 'YYYY-MM-DD HH:mm:ss'. If omitted, a cold-start will not be used.")
    parser.add_argument('-gage',
                        type=str,
                        help=f"Gage ID to run the forecast for. Default: {repr(c.DEFAULT_GAGE_ID)}")
    parser.add_argument('-forcing_configuration',
                        type=str,
                        help=f"Forcing configuration to use, e.g., 'short_range', 'standard_ana', etc. Default: {repr(c.FORECAST_FORCING_CONFIGURATION_TYPES__DEFAULT[0])}")
    parser.add_argument(
        "--fcst_run_name",
        type=str,
        help=f"Forecast run name. Default: {repr(c.DEFAULT_FORECAST_RUN_NAME)}",
    )
    parser.add_argument(
        "-n", "--nprocs",
        type=int,
        help=f"""
Currently only affects Calibration. Replaces default value for nprocs ({repr(c.DEFAULT_NPROCS)}) and subsequently the ParallelConfig instance.
When nprocs is 1, Calibration's ParallelConfig is: {make_parallel_config(nprocs=1)}.
When nprocs > 1, Calibration's ParallelConfig is like: {make_parallel_config(nprocs=2)}
""",
    ),
    parser.add_argument("--skip_calibration", action="store_true", help="Causes calibration to be skipped")

    if args_list is not None:
        return parser.parse_args(args_list)
    else:
        return parser.parse_args()


def main():
    options = get_options()
    
    forecast_vars = set_vars(options)
    fcst_kwargs = create_kwargs(forecast_vars)
    
    #fcst_deltas = const.forecast_constants()

    #util_asserts.assert_paths__core(forecast_vars.gage_id)
    #util_asserts.assert_paths__raw_config()
    #util_asserts.assert_paths_common_input()

    ### NOTE this deletes the test output dir.
    ### If wanting to skip Calibration but still do CS and/or Forecast,
    ### then remove this line so that the test calibration results remain available.
    #util_deletes.delete_test_output_dir(forecast_vars)
    #util_deletes.delete_scratch_and_esmf_outputs(forecast_vars)
    
    if not options.skip_calibration:
        calibration__build_and_run(forecast_vars)

    # TODO pseudocode for now for states.
    #saved_start_states_pseudocode: list[SavedStartState_PseudoCode] = []

    if options.cold_start_datetime:
        rb_cs = build_coldstart_realization(fcst_kwargs, forecast_vars)
        print(f'Running coldstart realization: {rb_cs.input_configs["Forcing"]}')
        run_fcst(valid_yaml=forecast_vars.valid_best_yaml, real_path=str(rb_cs.realization_file))
    
    if options.cycle_datetime:
        rb_fcst = build_forecast_realization(fcst_kwargs)
        print(f'Running forecast realization: {rb_fcst.input_configs["Forcing"]}')
        run_fcst(valid_yaml=forecast_vars.valid_best_yaml, real_path=str(rb_fcst.realization_file))

    #saved_start_states_pseudocode.append(
    #    SavedStartState_PseudoCode(
    #        forecast_type=rb_cs.input_configs["Forcing"]["forcing_configuration"],
    #        cycle_datetime=COLDSTART_END,
    #        realization_file=rb_cs.realization_file,
    #    )
    #)

    #for rb_fcst in forecast_multiple_workflow.generate_forecasts(fcst_kwargs, forecast_vars, fcst_deltas):
    #    print(f'Running forecast realization: {rb_fcst.input_configs["Forcing"]}')
    #    run_fcst(valid_yaml=forecast_vars.valid_best_yaml, real_path=str(rb_fcst.realization_file))
        
        
        #if rb_fcst.input_configs["Forcing"]["forcing_configuration"] == "standard_ana":
        #    sss = SavedStartState_PseudoCode(
        #        forecast_type=rb_fcst.input_configs["Forcing"]["forcing_configuration"],
        #        cycle_datetime=datetime.strptime(
        #            rb_fcst.input_configs["Forcing"]["cycle_datetime"], mswm_settings.DEFAULT_DATETIME_FORMAT
        #        ),
        #        realization_file=rb_fcst.realization_file,
        #    )
        #    saved_start_states_pseudocode.append(sss)


if __name__ == "__main__":
    main()
