import numpy as np
from pydantic import BaseModel,Field

from .deviceaccess import DeviceAccess
from .readback_value import Value

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
    """
    Class that implements a default device class that just prints out 
    values (Debugging purpose)
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self._setpoint = cfg.setpoint
        self._readback = cfg.readback
        self._unit = cfg.unit
        self._cache = 0.0

    def name(self) -> str:
        return self._setpoint

    def measure_name(self) -> str:
        return self._readback

    def set(self, value: float):
        print(f"{self._setpoint}: set {value}")
        self._cache = value

    def set_and_wait(self, value: float):
        self.set(value)

    def get(self) -> float:
        return self._cache

    def readback(self) -> Value:
        return Value(self._cache)

    def unit(self) -> str:
        return self._unit
