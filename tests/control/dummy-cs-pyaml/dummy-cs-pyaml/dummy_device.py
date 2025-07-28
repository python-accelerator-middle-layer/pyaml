from pydantic import BaseModel

from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value

# Define the main class name for this module
PYAMLCLASS = "DummyDevice"


class ConfigModel(BaseModel):
    setpoint: str
    """Name of control system device value (i.e. a power supply current)"""
    readback: str
    """Measured value"""
    unit: str
    """Value unit"""


class DummyDevice(DeviceAccess):
    """
    Class that implements a default device class that just prints out
    values (Debugging purpose)
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        self._setpoint = cfg.setpoint
        self._readback = cfg.readback
        self._unit = cfg.unit
        self._cache = Value(0.0)

    def name(self) -> str:
        return self._setpoint

    def measure_name(self) -> str:
        return self._readback

    def set(self, value: float):
        self._cache = Value(value)

    def set_and_wait(self, value: float):
        self.set(value)

    def get(self) -> Value:
        return self._cache

    def readback(self) -> Value:
        return self._cache

    def unit(self) -> str:
        return self._unit
