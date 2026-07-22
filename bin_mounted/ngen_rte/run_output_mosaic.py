"""
Command-line executable to run the output mosaicing workflow from nwm-data-assimilation.
Calls data-assimilation's combine_basin_grids to merge per-timestep NetCDF gridded outputs into a single NetCDF product.
"""

import argparse

from data_assimilation_engine.netcdf_production_sample import combine_basin_grids

from ngen_rte.logger import initialize_logger
from ngen_rte.run_config import cli_args
from ngen_rte.utils import (
    _rte_transmit_job_complete,
    _rte_transmit_job_failed,
    _rte_transmit_job_start,
    transmit,
)

LOG = initialize_logger()


def _main(reference_grid: str, netcdf_folder: str, output_folder: str) -> None:

    LOG.info(f"Starting output mosaicing workflow using reference grid: {reference_grid}")
    combine_basin_grids(
        reference_grid=reference_grid,
        netcdf_folder=netcdf_folder,
        output_folder=output_folder,
    )
    LOG.info(f"Output mosaicing workflow complete. Combined outputs written to : {output_folder}")


def main(reference_grid: str, netcdf_folder: str, output_folder: str) -> None:
    _rte_transmit_job_start()
    try:
        _main(
            reference_grid=reference_grid,
            netcdf_folder=netcdf_folder,
            output_folder=output_folder,
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
    parser.add_args_for_script(parser, cli_args.Script.OUTPUT_POSTPROCESS)
    return parser


if __name__ == "__main__":
    parser = cli_arg_parser()
    args = parser.parse_args()
    main(
        reference_grid=args.reference_grid,
        netcdf_folder=args.netcdf_folder,
        output_folder=args.output_folder,
    )
