import numpy as np
from pydantic import BaseModel,Field

from .backend_loader import load_backend
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
    """
    Class that implements a default device class that just prints out 
    values (Debugging purpose)
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        backend_module = load_backend()
        device_cls = getattr(backend_module, "PYAMLCLASS")
        device_cls = getattr(backend_module, "Device")
        self._impl: DeviceAccess = device_cls(cfg)

    def name(self) -> str:
        return self._setpoint

    def measure_name(self) -> str:
        return self._readback
    
    def set(self, value: float):
        print("%s: set %f" % (self._setpoint, value))
        self._impl.set(value)

    def get(self) -> float:
        return self._impl.get()

    def readback(self) -> float:
        return self._impl.readback()

    def unit(self) -> str:
        return self._unit
