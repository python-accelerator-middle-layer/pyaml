from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict

from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value

from .attribute_store import get_state

PYAMLCLASS: str = "Attribute"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    attribute: str
    unit: str = ""
    range: Optional[Tuple[Optional[float], Optional[float]]] = None


class Attribute(DeviceAccess):
    """
    Class that implements a default device class that just prints out
    values (Debugging purpose)
    """

    def __init__(self, cfg: ConfigModel, is_array=False):
        super().__init__()
        self._cfg = cfg
        self._setpoint = cfg.attribute
        self._readback = cfg.attribute
        get_state(cfg.attribute, unit=cfg.unit, range=self._range())

    def set_array(self, is_array: bool):
        get_state(
            self._cfg.attribute,
            unit=self._cfg.unit,
            range=self._range(),
        ).is_array = is_array

    def name(self) -> str:
        return self._setpoint

    def measure_name(self) -> str:
        return self._readback

    def set(self, value):
        print(f"{self._cfg.attribute}:{value}")
        state = get_state(self._cfg.attribute, unit=self._cfg.unit, range=self._range())
        state.value = value

    def set_and_wait(self, value):
        self.set(value)

    def get(self):
        state = get_state(self._cfg.attribute, unit=self._cfg.unit, range=self._range())
        return state.value

    def readback(self):
        state = get_state(
            self._cfg.attribute,
            unit=self._cfg.unit,
            range=self._range(),
        )
        value = state.value if state.readback is None else state.readback
        if state.is_array:
            return [Value(v) for v in value]
        return Value(value)

    def unit(self) -> str:
        state = get_state(self._cfg.attribute, unit=self._cfg.unit, range=self._range())
        return state.unit

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)

    def get_range(self) -> list[float]:
        state = get_state(
            self._cfg.attribute,
            unit=self._cfg.unit,
            range=self._range(),
        )
        if state.range is None:
            return [None, None]
        return [
            state.range[0] if state.range[0] is not None else None,
            state.range[1] if state.range[1] is not None else None,
        ]

    def check_device_availability(self) -> bool:
        return True

    def _range(self):
        return getattr(self._cfg, "range", None)
