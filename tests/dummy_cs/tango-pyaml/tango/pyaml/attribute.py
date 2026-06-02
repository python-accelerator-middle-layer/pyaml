from typing import Optional

from pydantic import BaseModel, ConfigDict

from pyaml.common.exception import PyAMLException
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value

from .attribute_store import get_state

PYAMLCLASS: str = "Attribute"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    attribute: str
    unit: str = ""
    range: Optional[tuple[Optional[float], Optional[float]]] = None
    index: Optional[int] = None


class Attribute(DeviceAccess):
    """
    Dummy attribute backed by a shared in-memory state store.

    When ``index`` is set the attribute presents a read-only scalar view of
    one element of a vector attribute; writes are rejected and the underlying
    store is automatically marked as an array.
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        self._index = cfg.index
        state = get_state(cfg.attribute, unit=cfg.unit, range=cfg.range)
        if self._index is not None:
            state.is_array = True

    def set_array(self, is_array: bool):
        """Mark the shared value as array-like without initializing it."""
        get_state(self._cfg.attribute, unit=self._cfg.unit, range=self._cfg.range).is_array = is_array

    def name(self) -> str:
        if self._index is not None:
            return f"{self._cfg.attribute}[{self._index}]"
        return self._cfg.attribute

    def measure_name(self) -> str:
        return self.name()

    def set(self, value):
        if self._index is not None:
            raise PyAMLException(
                f"Indexed attribute '{self._cfg.attribute}[{self._index}]' does not support individual element writes."
            )
        state = get_state(self._cfg.attribute, unit=self._cfg.unit, range=self._cfg.range)
        state.value = value

    def set_and_wait(self, value):
        self.set(value)

    def get(self):
        state = get_state(self._cfg.attribute, unit=self._cfg.unit, range=self._cfg.range)
        if self._index is not None:
            return state.value[self._index]
        return state.value

    def readback(self):
        """Return readback from shared state, preserving scalar/array shape."""
        state = get_state(self._cfg.attribute, unit=self._cfg.unit, range=self._cfg.range)
        value = state.value if state.readback is None else state.readback
        if self._index is not None:
            return Value(value[self._index])
        if state.is_array:
            return [Value(v) for v in value]
        return Value(value)

    def unit(self) -> str:
        return get_state(self._cfg.attribute, unit=self._cfg.unit, range=self._cfg.range).unit

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)

    def get_range(self) -> list[float]:
        state = get_state(self._cfg.attribute, unit=self._cfg.unit, range=self._cfg.range)
        if state.range is None:
            return [None, None]
        return [state.range[0], state.range[1]]

    def check_device_availability(self) -> bool:
        return True
