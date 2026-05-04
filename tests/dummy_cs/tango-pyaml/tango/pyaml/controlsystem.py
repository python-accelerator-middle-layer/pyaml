import copy
from typing import Any

from pydantic import BaseModel, ConfigDict

from pyaml import PyAMLException
from pyaml.configuration.catalog import Catalog
from pyaml.control.controlsystem import ControlSystem
from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS: str = "TangoControlSystem"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    tango_host: str | None = None
    catalog: Catalog | str | None = None
    debug_level: str | None = None
    lazy_devices: bool = True
    scalar_aggregator: str | None = "tango.pyaml.multi_attribute"
    vector_aggregator: str | None = None
    timeout_ms: int = 3000


class TangoControlSystem(ControlSystem):
    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        self.__devices = {}

    def attach_array(self, devs: list[DeviceAccess | None]) -> list[DeviceAccess | None]:
        return self._attach(devs, True)

    def attach(self, devs: list[DeviceAccess | None]) -> list[DeviceAccess | None]:
        return self._attach(devs, False)

    def get_device(self, ref: str | BaseModel | None) -> DeviceAccess | None:
        if ref is None:
            return None

        if isinstance(ref, str):
            if self._catalog is None:
                raise PyAMLException(f"Control system '{self.name()}' has no catalog configured for key '{ref}'")
            try:
                dev = self._catalog.resolve(ref)
            except AttributeError as exc:
                raise PyAMLException(f"Control system '{self.name()}' catalog cannot resolve key '{ref}'") from exc
            return self.attach([dev])[0]

        from .attribute import Attribute
        from .attribute import ConfigModel as AttributeConfigModel

        if isinstance(ref, AttributeConfigModel):
            return self.attach([Attribute(ref)])[0]

        raise PyAMLException(f"Control system '{self.name()}' cannot build a device from {type(ref).__name__}")

    def _attach(self, devs: list[DeviceAccess | None], is_array: bool) -> list[DeviceAccess | None]:
        newDevs = []
        for d in devs:
            if d is not None:
                if self._cfg.tango_host:
                    full_name = "//" + self._cfg.tango_host + "/" + d._cfg.attribute
                else:
                    full_name = d._cfg.attribute
                index = getattr(d._cfg, "index", None)
                cache_key = full_name if index is None else f"{full_name}[{index}]"
                if cache_key not in self.__devices:
                    newDev = copy.copy(d)
                    newDev._cfg = copy.copy(d._cfg)
                    newDev._cfg.attribute = full_name
                    newDev.set_array(is_array)
                    self.__devices[cache_key] = newDev
                newDevs.append(self.__devices[cache_key])
            else:
                newDevs.append(None)
        return newDevs

    def name(self) -> str:
        return self._cfg.name

    def get_catalog_config(self) -> Catalog | str | None:
        return self._cfg.catalog

    def scalar_aggregator(self) -> str | None:
        return self._cfg.scalar_aggregator

    def vector_aggregator(self) -> str | None:
        return self._cfg.vector_aggregator

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
