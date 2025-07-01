"""
Class that implements a Default device class that just prints out values
"""

import numpy as np
from pydantic import BaseModel

from .DeviceAccess import DeviceAccess

class Config(BaseModel):

    setpoint: str
    readback: str
    unit: str


class Device(DeviceAccess):

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._setpoint = cfg.setpoint
        self._readback = cfg.readback
        self._unit = cfg.unit
        self._cache = 0.0  # Debugging purpose

    # Sets the value
    def set(self, value: float):
        print("%s: set %f" % (self._setpoint, value))
        self._cache = value

    # Get the setpoint
    def get(self) -> float:
        return self._cache

    # Get the measured value
    def readback() -> float:
        return self._cache

    # Get the unit
    def unit(self) -> str:
        return self._unit