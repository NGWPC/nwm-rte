
from datetime import datetime, timedelta
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

import consts as c


class CalibTimeWindows(BaseModel):
    """Calibration time windows defined by a start time
    and some timedelta offsets."""
    calib_sim_start: datetime = Field(default=c.CALIB_SIM_START_DEFAULT)
    calib_sim_duration: timedelta = Field(default=c.CALIB_SIM_DURATION_DEFAULT)
    calib_eval_delayment: timedelta = Field(default=c.CALIB_EVAL_DELAYMENT_DEFAULT)  # Delayed start from calibration simulation, for warmup
    valid_sim_advancement: timedelta = Field(default=c.VALID_SIM_ADVANCEMENT_DEFAULT)  # Validation simulation starts before calibration simulation, by this amount
    valid_eval_curtailment: timedelta = Field(default=c.VALID_EVAL_CURTAILMENT_DEFAULT)  # Valid eval window cut short by this amount

    @property
    def calib_sim_end(self) -> datetime:
        return self.calib_sim_start + self.calib_sim_duration
    
    @property
    def calib_eval_start(self) -> datetime:
        return self.calib_sim_start + self.calib_eval_delayment
    
    @property
    def calib_eval_end(self) -> datetime:
        return self.calib_sim_end

    @property
    def valid_sim_start(self) -> datetime:
        return self.calib_sim_start - self.valid_sim_advancement
    
    @property
    def valid_sim_end(self) -> datetime:
        return self.calib_sim_end
    
    @property
    def valid_eval_start(self) -> datetime:
        return self.calib_sim_start
    
    @property
    def valid_eval_end(self) -> datetime:
        return self.calib_sim_end - self.valid_eval_curtailment
    
    @property
    def full_eval_start(self) -> datetime:
        return self.calib_sim_start

    @property
    def full_eval_end(self) -> datetime:
        return self.calib_sim_end
    