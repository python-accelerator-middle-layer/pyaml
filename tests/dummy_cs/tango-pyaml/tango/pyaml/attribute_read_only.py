from pydantic import BaseModel, ConfigDict

from pyaml.control.readback_value import Value

from .attribute import Attribute

PYAMLCLASS: str = "AttributeReadOnly"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    attribute: str
    unit: str = ""


class AttributeReadOnly(Attribute):
    """
    Class that implements a default device class that just prints out
    values (Debugging purpose)
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)

    def set(self, value):
        raise Exception(f"{self._cfg.attribute} is read only attribute")

    def set_and_wait(self, value):
        raise Exception(f"{self._cfg.attribute} is read only attribute")

    def unit(self) -> str:
        return self._unit

    def get_range(self) -> list[float]:
        return [None, None]

    def check_device_availability(self) -> bool:
        return True
