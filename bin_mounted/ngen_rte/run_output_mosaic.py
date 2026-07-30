"""
Command-line executable to run the output mosaicing workflow from nwm-data-assimilation.
Calls data-assimilation's combine_basin_grids to merge per-timestep NetCDF gridded outputs into a single NetCDF product.
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
    netcdf_folder: str,
    output_folder: str,
    config_json_file: str,
    output_cycle_hour: int,
    output_cycle_type: str,
    output_cycle_domain: str,
) -> None:

    LOG.info(f"Starting output mosaicing workflow for directory: {netcdf_folder}")
    args_list = [
        netcdf_folder,
        output_folder,
        config_json_file,
        str(output_cycle_hour),
        output_cycle_type,
        output_cycle_domain,
        "mosaic",
    ]
    netcdf_production_workflow(args_list)
    LOG.info(f"Output mosaicing workflow complete. Combined outputs written to : {output_folder}")


def main(
    netcdf_folder: str,
    output_folder: str,
    config_json_file: str,
    output_cycle_hour: int,
    output_cycle_type: str,
    output_cycle_domain: str,
) -> None:
    _rte_transmit_job_start()
    try:
        _main(
            netcdf_folder=netcdf_folder,
            output_folder=output_folder,
            config_json_file=config_json_file,
            output_cycle_hour=output_cycle_hour,
            output_cycle_type=output_cycle_type,
            output_cycle_domain=output_cycle_domain,
        )
    except Exception as e:
        transmit(exc=e)
        _rte_transmit_job_failed()
        raise e
    else:
        _rte_transmit_job_complete()


def cli_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Combine NetCDF gridded outputs from multiple runs into a single NetCDF product.",
        formatter_class=cli_args.HelpFormatter,
    )
    cli_args.add_args_for_script(parser, cli_args.Script.OUTPUT_MOSAIC)
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    main(
        netcdf_folder=args.netcdf_folder,
        output_folder=args.output_folder,
        config_json_file=args.config_json_file,
        output_cycle_hour=args.output_cycle_hour,
        output_cycle_type=args.output_cycle_type,
        output_cycle_domain=args.output_cycle_domain,
    )
