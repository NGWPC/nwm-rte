"""
Command-line executable to build and run a series of "forecast" realizations, optionally with a "calibration" realization preceding them.

This runs inside the ngen runtime environment.
The CLI structure is mimicked in part by `configs.RTETestConfig`.
For settings that are not exposed by CLI arguments, see primarily `consts.py`.

When realizations fail, this program does not halt, but rather moves to the next configuration type in the list, with the
goal of "trying" many different realization configurations in one call. The status of each configuration's build step and
run step is reported and written to a json file at the end.

This includes options for stopping realizations mid-way through their run, rather than waiting for them to complete.

See `run_tests.sh` for example calls.
"""

import argparse
import json
import sys

from calib.strategy import (
    Algorithm as CalOptimizationAlgo,
)
from pydantic.json import pydantic_encoder

from ngen_rte import consts as c
from ngen_rte.configs import RTETestConfig
from ngen_rte.logger import initialize_logger
from ngen_rte.run_config import cli_args
from ngen_rte.tests import utils_testing_setup
from ngen_rte.tests.execution_tests import (
    ForecastTest,
    TestsManager,
    TestStat,
    get_test_configs__calibration,
    get_test_configs__forecast,
)
from ngen_rte.utils import (
    _rte_transmit_job_complete,
    _rte_transmit_job_start,
)

LOG = initialize_logger()


def calibrations__build_and_run(cfg: RTETestConfig, tm: TestsManager) -> None:
    """Build calibration realizations and run them as tests."""
    perms = cfg.get_calib_permutations()
    for obj_func, optim_algo, _ in perms:
        rte_calib_configs = get_test_configs__calibration(
            cfg,
            obj_func=obj_func,
            optim_algo=optim_algo,
        )

        for i, calib_config in enumerate(rte_calib_configs):
            fc = calib_config.forcing_configuration
            worker_name = (
                f"test_{i}_{calib_config.mswm_GeneralConfig.models.replace(',', '_')}_rootzone={calib_config.mswm_ModulePropertiesConfig.cfe_aet_rootzone}"
                if optim_algo == CalOptimizationAlgo.dds
                else None
            )
            rb_kwargs = calib_config.mswm_RealizationBuilder_kwargs
            msg_prefix = f"i={i} (ilimit={len(rte_calib_configs) - 1}) worker_name={worker_name} Calibration with forcing={repr(fc)}, models={repr(calib_config.mswm_GeneralConfig.models)}, cfe_aet_rootzone={calib_config.mswm_ModulePropertiesConfig.cfe_aet_rootzone}, obj_func={repr(obj_func.value)}, optim_algo={repr(optim_algo.value)}, obs_dir={calib_config.mswm_DataFileConfig.obs_dir}, nwmretro_file={calib_config.mswm_DataFileConfig.nwmretro_file}"

            if cfg.restart and i + 1 <= len(tm.prev_results):
                LOG.info(f"Skipping since restart={cfg.restart}: {msg_prefix}")
                continue

            LOG.info(
                f"\n\n##########\n### {msg_prefix}: setting up test with rb_kwargs = \n{json.dumps(rb_kwargs, indent=2, default=pydantic_encoder)}"
            )
            t = ForecastTest(rb_kwargs=rb_kwargs)

            # Build the realization, trapping exceptions into class attrs
            LOG.info(f"### {msg_prefix}: building realization")
            t.make_realization_builder__build_realization(
                build_method="build_calib_realization"
            )

            if t.rb_stat == TestStat.PASS:
                cfg.configure_ngen_log(t.rb)
                # Execute the realization via ngen, trapping exceptions and logs into class attrs
                LOG.info(f"### {msg_prefix}: executing calibration realization")
                t.execute_calibration(
                    cfg.quit_calibration_after_duration, worker_name=worker_name
                )

            tm.add_forecast_test(t)
            tm.evaluate_test_results(raise_if_any_failed=False, header_prefix="INTERIM")


def forecasts__build_and_run(cfg: RTETestConfig, tm: TestsManager, cs: bool) -> None:
    """
    Using ForecastTest, build and execute a list of forecast realizations.
    tests_manager is modified in-place, so some test results may be available if this function is interrupted.
    `cs` controls whether coldstart is used (not `cfg.do_coldstart`).
    """
    for obj_func, optim_algo, test_paths in cfg.get_calib_permutations():
        test_configs = get_test_configs__forecast(cfg, use_cold_start=cs)
        for i, config_overrides in enumerate(test_configs):
            fc = config_overrides.Forcing.forcing_configuration
            msg_prefix = f"i={i} (ilimit={len(test_configs) - 1}) forecast {repr(fc)} with calib obj_func={repr(obj_func.value)}, optim_algo={repr(optim_algo.value)}"

            if cfg.restart and i + 1 <= len(tm.prev_results):
                LOG.info(f"Skipping since restart={cfg.restart}: {msg_prefix}")
                continue

            rb_kwargs = {
                # "input_path": test_paths.dir_input,
                "valid_yaml": test_paths.valid_yaml,
                "fcst_run_name": cfg._fcst_run_name_formatted,
                "config_overrides": config_overrides,
                "use_cold_start": cs,
            }
            LOG.info(
                f"\n\n##########\n### {msg_prefix}: setting up test with rb_kwargs = {rb_kwargs}"
            )

            t = ForecastTest(rb_kwargs=rb_kwargs)

            # Build the realization, trapping exceptions into class attrs
            LOG.info(f"### {msg_prefix}: building realization")
            t.make_realization_builder__build_realization(
                build_method="build_fcst_realization"
            )

            if t.rb_stat == TestStat.PASS:
                # Execute the realization via ngen, trapping exceptions and logs into class attrs
                cfg.configure_ngen_log(t.rb)
                LOG.info(f"### {msg_prefix}: executing realization via ngen")
                t.execute_forecast(
                    quit_forecast_after_duration=cfg.quit_forecast_after_duration
                )

            tm.add_forecast_test(t)
            tm.evaluate_test_results(raise_if_any_failed=False, header_prefix="INTERIM")


def run_noop_mode() -> None:
    """Run noop mode - verify imports and basic setup without executing workflows."""
    LOG.info("\nRunning in noop mode - only checking imports and basic setup.")
    LOG.info("Successfully imported all required libraries.")
    LOG.info("Noop mode complete - exiting")
    sys.exit(0)  # Exit the program directly


def main(cfg: RTETestConfig):
    _rte_transmit_job_start()

    if cfg.noop:
        run_noop_mode()

    utils_testing_setup.assert_paths__core(cfg)
    # utils_testing_setup.assert_paths__raw_config(cfg)
    ### NOTE this deletes the test output dir.
    ### If wanting to skip Calibration but still do CS and/or Forecast,
    ### then remove this line so that the test calibration results remain available.
    # utils_testing_setup.delete_test_output_dir(cfg)

    if cfg.delete_scratch_and_mesh_first:
        utils_testing_setup.delete_scratch_and_esmf_outputs(cfg)
    if cfg.delete_forcing_raw_input_first:
        utils_testing_setup.delete_forcing_raw_inputs()

    tm = TestsManager(restart=cfg.restart)

    if cfg.do_calibration:
        calibrations__build_and_run(cfg, tm)

    if cfg.do_coldstart:
        forecasts__build_and_run(cfg, tm, cs=True)
    if not cfg.skip_forecast:
        forecasts__build_and_run(cfg, tm, cs=False)

    tm.evaluate_test_results(header_prefix="FINAL")

    _rte_transmit_job_complete()


def cli_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="""Script for building and running a series of test
realizations, optionally including calibration, coldstart, and forecasts,
using various forcing configurations and model formulations.""",
        formatter_class=cli_args.HelpFormatter,
    )
    cli_args.add_args_for_script(parser, cli_args.Script.TESTS)

    parser = argparse.ArgumentParser(
        description="""Script for building and running a series of test
realizations, optionally including calibration, coldstart, and forecasts,
using various forcing configurations and model formulations.""",
        formatter_class=cli_args.HelpFormatter,
    )
    parser.add_argument(
        "-nofcst",
        "--skip_forecast",
        action="store_true",
        help="""Provide to skip forecast (for testing calibrations only).
Incompatible with --do_all_forcing_configs and --do_coldstart""",
    )
    parser.add_argument(
        "-quitfcdur",
        "--quit_forecast_after_duration",
        default=None,
        type=float,
        help="""Instead of waiting for each forecast to finish,
quit after the specified elapsed processing duration in seconds.""",
    )
    parser.add_argument(
        "-calib",
        "--do_calibration",
        action="store_true",
        help="Build and run a calibration before forecasts.",
    )
    parser.add_argument(
        "-quitcaldur",
        "--quit_calibration_after_duration",
        default=None,
        type=float,
        help="""For calibrations, instead of waiting for the realization
to finish, quit after the specified processing duration. Units: seconds.""",
    )
    parser.add_argument(
        "-ofuncs",
        "--objective_functions",
        nargs="+",
        type=c.CalObjective,
        default=[c.CALIB_OBJECTIVE_FUNCTION],
        help="List of objective functions for calibration.",
    )
    parser.add_argument(
        "-allofuncs",
        "--do_all_objective_functions",
        action="store_true",
        help=f"For calibration, causes all objective functions to be executed: {cli_args.split_iter_to_chunked_str([_.value for _ in c.CalObjective])}",
    )
    parser.add_argument(
        "-optalgos",
        "--optimization_algorithms",
        nargs="+",
        type=c.CalOptimizationAlgo,
        default=[c.CALIB_OPTIMIZATION_ALGO],
        help="List of optimization algorithms for calibration.",
    )
    parser.add_argument(
        "-alloptalgos",
        "--do_all_optimization_algorithms",
        action="store_true",
        help=f"For calibration, causes all optimization algorithms to be executed: {cli_args.split_iter_to_chunked_str([_.value for _ in c.CalOptimizationAlgo])}",
    )
    parser.add_argument(
        "-allforcings",
        "--do_all_forcing_configs",
        action="store_true",
        help=f"""Run all forcing configurations rather than the default shorter default list.
For reference, the default list is: {c.FORECAST_FORCING_TYPES__TESTS}.
Incompatible with --skip_forecast.""",
    )
    parser.add_argument(
        "-mff",
        "--model_formulations_file",
        help=f"""If provided, multiple model formulations will be ran,
and this is a file path to a tsv file of the formulations list. If not provided,
then the default model formulation will be used: {c.DEFAULT_MODEL_FORMULATION_ARGS}.""",
    )
    parser.add_argument(
        "-calfsrcs",
        "--calibration_forcing_sources",
        nargs="*",
        default=c.CALIB_FORCING_TYPES,
        help=f"""Sources of forcing data for calibration runs. If not provided,
then this default will be used: {c.CALIB_FORCING_TYPES}.""",
    )
    parser.add_argument(
        "-cs",
        "--do_coldstart",
        action="store_true",
        help="Causes use_cold_start to be True for all forecasts",
    )
    parser.add_argument(
        "--noop",
        action="store_true",
        help="""Run in noop mode - only verify that the script
can import libraries and basic setup, then exit without looking
for data or running any workflows.""",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help=f"""Run in restart mode. Read existing results json file {repr(c.TEST_RESULTS_FILE)}
if it exists, and skip indexes that already have a record in it.""",
    )
    cli_args.add_args_for_script(parser, cli_args.Script.TESTS)
    args = parser.parse_args()
    LOG.info(f"{__file__}: args: {json.dumps(vars(args), indent=2)}")

    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    main(cfg=RTETestConfig(**vars(args)))
