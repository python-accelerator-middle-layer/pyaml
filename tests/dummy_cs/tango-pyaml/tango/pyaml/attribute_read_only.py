from pydantic import BaseModel,ConfigDict
from .attribute import Attribute
from pyaml.control.readback_value import Value

PYAMLCLASS : str = "AttributeReadOnly"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    attribute: str
    unit: str = ""

class AttributeReadOnly(Attribute):
    """
    Class that implements a default device class that just prints out 
    values (Debugging purpose)
    """
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)
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
        raise Exception(f"{self._cfg.attribute} is read only attribute")

    def set_and_wait(self, value: float):
        raise Exception(f"{self._cfg.attribute} is read only attribute")

    def get(self) -> float:
        return self._cache

    def readback(self) -> Value:
        return Value(self._cache)

    def unit(self) -> str:
        return self._unit
