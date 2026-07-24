"""
Command-line executable to run the overall NetCDF production workflow from nwm-data-assimilation.
Calls data-assimilation's overall_netcdf_workflow to convert ngen catchment output into NWM-formatted gridded NetCDF products.
"""

import argparse

from data_assimilation_engine.output_variables.NetCdfProductionManager import netcdf_production_workflow

from ngen_rte.logger import initialize_logger
from ngen_rte.run_config import cli_args
from ngen_rte.utils import (
    _rte_transmit_job_complete,
    _rte_transmit_job_failed,
    _rte_transmit_job_start,
    transmit,
)

LOG = initialize_logger()


def _main(
        ngen_netcdf_output_file: str,
        ngen_gpkg_file: str,
        output_folder: str,
        config_json_file: str,
        output_cycle_hour: int,
        output_cycle_type: str,
        troute_output_file: str = "",
        troute_lakeout_file: str = "",
        output_templates_folder: str = ""
) -> None:

    LOG.info(f"Starting NetCDF production workflow for: {ngen_netcdf_output_file}")
    args_list = [
        output_folder,
        ngen_netcdf_output_file,
        ngen_gpkg_file,
        troute_output_file,
        troute_lakeout_file,
        config_json_file,
        output_templates_folder,
        output_cycle_hour,
        output_cycle_type,
        "all",
    ]
    netcdf_production_workflow(args_list)
    LOG.info(f"NetCDF production workflow complete. Outputs written to: {output_folder}")


def main(
    ngen_netcdf_output_file: str,
    ngen_gpkg_file: str,
    output_folder: str,
    config_json_file: str,
    output_cycle_hour: int,
    output_cycle_type: str,
    troute_output_file: str = "",
    troute_lakeout_file: str = "",
    output_templates_folder: str = "",
) -> None:
    _rte_transmit_job_start()
    try:
        _main(
            ngen_netcdf_output_file=ngen_netcdf_output_file,
            ngen_gpkg_file=ngen_gpkg_file,
            output_folder=output_folder,
            config_json_file=config_json_file,
            output_cycle_hour=output_cycle_hour,
            output_cycle_type=output_cycle_type,
            troute_output_file=troute_output_file,
            troute_lakeout_file=troute_lakeout_file,
            output_templates_folder=output_templates_folder
        )
    except Exception as e:
        transmit(exc=e)
        _rte_transmit_job_failed()
        raise e
    else:
        _rte_transmit_job_complete()


def cli_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run NetCDF production workflow to convert ngen catchment output into NWM gridded NetCDF products.",
        formatter_class=cli_args.HelpFormatter,
    )
    cli_args.add_args_for_script(parser, cli_args.Script.OUTPUT_POSTPROCESS)
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    main(
        ngen_netcdf_output_file=args.ngen_netcdf_output_file,
        ngen_gpkg_file=args.ngen_gpkg_file,
        output_folder=args.output_folder,
        config_json_file=args.config_json_file,
        output_cycle_hour=args.output_cycle_hour,
        output_cycle_type=args.output_cycle_type,
        troute_output_file=args.troute_output_file,
        troute_lakeout_file=args.troute_lakeout_file,
        output_templates_folder=args.output_templates_folder
    )
