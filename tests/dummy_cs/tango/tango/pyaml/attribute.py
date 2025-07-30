from pydantic import BaseModel
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value

PYAMLCLASS : str = "Attribute"

class ConfigModel(BaseModel):
    attribute: str
    unit: str = ""

class Attribute(DeviceAccess):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)

    """
    Class that implements a default device class that just prints out 
    values (Debugging purpose)
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self._setpoint = cfg.attribute
        self._readback = cfg.attribute
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
