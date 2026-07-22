"""
Command-line executable to run the overall NetCDF production workflow from nwm-data-assimilation.
Calls data-assimilation's overall_netcdf_workflow to convert ngen catchment output into NWM-formatted gridded NetCDF products.
"""

import argparse

from data_assimilation_engine.netcdf_production_sample import overall_netcdf_workflow

from ngen_rte.logger import initialize_logger
from ngen_rte.run_config import cli_args
from ngen_rte.utils import (
    _rte_transmit_job_complete,
    _rte_transmit_job_failed,
    _rte_transmit_job_start,
    transmit,
)

LOG = initialize_logger()


def _main(ngen_netcdf_output_file: str, ngen_gpkg_file: str, output_folder: str, troute_output_file: str = "", troute_lakeout_file: str = "") -> None:

    LOG.info(f"Starting NetCDF production workflow for: {ngen_netcdf_output_file}")
    overall_netcdf_workflow(
        ngen_netcdf_output_file=ngen_netcdf_output_file,
        ngen_gpkg_file=ngen_gpkg_file,
        output_folder=output_folder,
        troute_output_file=troute_output_file,
        troute_lakeout_file=troute_lakeout_file,
    )
    LOG.info(f"NetCDF production workflow complete. Outputs written to: {output_folder}")


def main(ngen_netcdf_output_file: str, ngen_gpkg_file: str, output_folder: str, troute_output_file: str = "", troute_lakeout_file: str = "") -> None:
    _rte_transmit_job_start()
    try:
        _main(
            ngen_netcdf_output_file=ngen_netcdf_output_file,
            ngen_gpkg_file=ngen_gpkg_file,
            output_folder=output_folder,
            troute_output_file=troute_output_file,
            troute_lakeout_file=troute_lakeout_file,
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
    parser.add_args_for_script(parser, cli_args.Script.OUTPUT_POSTPROCESS)
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    main(
        ngen_netcdf_output_file=args.ngen_netcdf_output_file,
        ngen_gpkg_file=args.ngen_gpkg_file,
        output_folder=args.output_folder,
        troute_output_file=args.troute_output_file,
        troute_lakeout_file=args.troute_lakeout_file,
    )
