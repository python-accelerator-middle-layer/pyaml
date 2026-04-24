from pydantic import BaseModel, ConfigDict

from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value

from .attribute_store import get_state

PYAMLCLASS: str = "AttributeIndexed"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    attribute: str
    index: int
    unit: str = ""


class AttributeIndexed(DeviceAccess):
    """
    Read-only DeviceAccess that extracts one scalar element from a vector attribute.

    Used when a single hardware attribute exposes a position vector and each
    catalog entry maps to one component identified by *index*.  The underlying
    vector attribute is registered in the shared state store so tests can
    pre-populate it with a list before loading the accelerator.
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        state = get_state(cfg.attribute, unit=cfg.unit)
        state.is_array = True

    def set_array(self, is_array: bool):
        # The underlying hardware attribute is always a vector; this device
        # presents a scalar view of it, so we always mark the store as array.
        get_state(self._cfg.attribute, unit=self._cfg.unit).is_array = True

    def name(self) -> str:
        return f"{self._cfg.attribute}[{self._cfg.index}]"

    def measure_name(self) -> str:
        return self.name()

    def set(self, value):
        raise Exception(f"{self._cfg.attribute}[{self._cfg.index}] is read only")

    def set_and_wait(self, value):
        raise Exception(f"{self._cfg.attribute}[{self._cfg.index}] is read only")

    def get(self):
        state = get_state(self._cfg.attribute, unit=self._cfg.unit)
        return state.value[self._cfg.index]

    def readback(self) -> Value:
        state = get_state(self._cfg.attribute, unit=self._cfg.unit)
        value = state.value if state.readback is None else state.readback
        return Value(value[self._cfg.index])

    def unit(self) -> str:
        return get_state(self._cfg.attribute, unit=self._cfg.unit).unit

    def get_range(self) -> list[float]:
        return []

    def check_device_availability(self) -> bool:
        return True
