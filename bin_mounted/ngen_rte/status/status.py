"""Status handling"""

import functools
import os

from ewts.data_payloads import Payload, extract_payload_from_log_msg
from mswm.build_inputs import RealizationBuilder
from ngen_rte.configs import (
    RTEBaseConfig,
    RTECalibConfig,
    RTEDefaultConfig,
    RTEForecastConfig,
    RTETestConfig,
)
from pydantic import BaseModel, ConfigDict

print = functools.partial(print, flush=True)


class NgenStatus(BaseModel):
    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    cfg: RTEBaseConfig
    rb: RealizationBuilder

    def model_post_init(self, __context) -> None:
        pass

    @property
    def ngen_log_dir(self):
        if str(self.rb.work_dir) != str(os.path.dirname(self.rb.realization_file)):
            raise ValueError(
                f"Expected RealizationBuilder work_dir to match parent of RealizationBuilder realization_file, but got: {self.rb.work_dir} vs {os.path.dirname(self.rb.realization_file)}."
            )
        if isinstance(self.cfg, RTEDefaultConfig):
            nld = self.rb.work_dir
        elif isinstance(self.cfg, RTECalibConfig):
            nld = self.rb.work_dir
        elif isinstance(self.cfg, RTEForecastConfig):
            nld = os.path.join(self.rb.work_dir, "Input")
        elif isinstance(self.cfg, RTETestConfig):
            raise NotImplementedError(f"Unsupported config type: {type(self.cfg)}")
        else:
            raise NotImplementedError(f"Unsupported config type: {type(self.cfg)}")
        return nld

    @property
    def ngen_log_dir_basename(self) -> str:
        return os.path.basename(self.ngen_log_dir)

    def ngen_log_basename(self, mpi_rank: int):
        if isinstance(self.cfg, RTEDefaultConfig):
            bn = f"{self.ngen_log_dir_basename}_ngen_mpi_process_{mpi_rank}.log"
        elif isinstance(self.cfg, RTECalibConfig):
            # NOTE determine where the 'calib' prefix is derived from and parameterize it instead of hardcoding it here.
            bn = f"calib_ngen_mpi_process_{mpi_rank}.log"
        elif isinstance(self.cfg, RTEForecastConfig):
            bn = f"{self.rb.fcst_run_name}_ngen_mpi_process_{mpi_rank}.log"
        elif isinstance(self.cfg, RTETestConfig):
            raise NotImplementedError(f"Unsupported config type: {type(self.cfg)}")
        else:
            raise NotImplementedError(f"Unsupported config type: {type(self.cfg)}")

        return bn

    def ngen_log(self, mpi_rank: int) -> str:
        return os.path.join(self.ngen_log_dir, self.ngen_log_basename(mpi_rank))

    @property
    def mpirank2ngenlog(self) -> dict[int, str]:
        """Mapping of MPI rank to ngen log file path"""
        d = {mpi_rank: self.ngen_log(mpi_rank) for mpi_rank in range(self.cfg.nprocs)}
        return d

    def mpirank2payloads(self) -> dict[int, list[Payload]]:
        """Mapping of MPI rank to list of payloads extracted from that rank's ngen log file."""
        d: dict[int, list[Payload]] = {}
        payload_count_per_rank: dict[int, int] = {r: 0 for r in range(self.cfg.nprocs)}
        for mpi_rank, ngen_log in self.mpirank2ngenlog.items():
            if not os.path.exists(ngen_log):
                raise FileNotFoundError(ngen_log)
            print(f"Reading: {ngen_log}")
            with open(ngen_log) as f:
                lines = f.readlines()
            for line in lines:
                payload = extract_payload_from_log_msg(line)
                if payload is not None:
                    d.setdefault(mpi_rank, []).append(payload)
                    payload_count_per_rank[mpi_rank] += 1
        print(f"Count of payloads per rank: {payload_count_per_rank}")
        return d

    def log_all_payloads(self):
        """Log all payloads extracted from all MPI ranks' ngen log files."""
        print("About to extract all payloads from all MPI ranks' ngen log files...")
        for mpi_rank, payloads in self.mpirank2payloads().items():
            payloads_lines = "\n".join(map(str, payloads))
            print(
                f"\nMPI rank {mpi_rank} had {len(payloads)} payloads extracted from its log file: {self.ngen_log(mpi_rank)}. Payloads:\n{payloads_lines}"
            )
