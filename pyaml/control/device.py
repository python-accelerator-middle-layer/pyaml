"""
Class that implements a default device class that just prints out values (Debugging purpose)
"""

import numpy as np
from pydantic import BaseModel,Field

from .deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "Device"

class ConfigModel(BaseModel):

    setpoint: str
    """Name of control system device value (i.e. a power supply current)"""
    readback: str
    """Measured value"""
    unit: str
    """Value unit"""

class Device(DeviceAccess):

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self._setpoint = cfg.setpoint
        self._readback = cfg.readback
        self._unit = cfg.unit
        self._cache = 0.0

    def name(self) -> str:
        return self._setpoint

    def measure_name(self):
        return self._readback
    
    def set(self, value: float):
        print("%s: set %f" % (self._setpoint, value))
        self._cache = value

    def get(self) -> float:
        return self._cache

    def readback() -> float:
        return self._cache

    def unit(self) -> str:
        return self._unit