from pydantic import BaseModel,ConfigDict
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value

PYAMLCLASS : str = "Attribute"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    attribute: str
    unit: str = ""

class Attribute(DeviceAccess):
    """
    Class that implements a default device class that just prints out 
    values (Debugging purpose)
    """
    def __init__(self, cfg: ConfigModel):
        super().__init__()
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
        self._cache = value

    def set_and_wait(self, value: float):
        self.set(value)

    def get(self) -> float:
        return self._cache

    def readback(self) -> Value:
        return Value(self._cache)

    def unit(self) -> str:
        return self._unit

    def __repr__(self):
       return repr(self._cfg).replace("ConfigModel",self.__class__.__name__)