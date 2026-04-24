import copy
import os

from pydantic import BaseModel, ConfigDict

from pyaml.configuration.catalog import Catalog
from pyaml.control.controlsystem import ControlSystem
from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS: str = "TangoControlSystem"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    tango_host: str
    catalog: Catalog | str | None = None
    debug_level: str = None


class TangoControlSystem(ControlSystem):
    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        print(f"Creating dummy TangoControlSystem: {cfg.name}")
        self.__DEVICES = {}

    def attach_array(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        return self._attach(devs, True)

    def attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        return self._attach(devs, False)

    def _attach(self, devs: list[DeviceAccess], is_array: bool) -> list[DeviceAccess]:
        newDevs = []
        for d in devs:
            if d is not None:
                full_name = "//" + self._cfg.tango_host + "/" + d._cfg.attribute
                # Include the index (if any) so that two AttributeIndexed devices
                # pointing to the same vector attribute but different indices get
                # separate entries in the cache.
                index = getattr(d._cfg, "index", None)
                cache_key = full_name if index is None else f"{full_name}[{index}]"
                if cache_key not in self.__DEVICES:
                    # Shallow copy the object
                    newDev = copy.copy(d)
                    # Shallow copy the config object
                    # to allow a new attribute name
                    newDev._cfg = copy.copy(d._cfg)
                    newDev._cfg.attribute = full_name
                    newDev.set_array(is_array)
                    self.__DEVICES[cache_key] = newDev
                newDevs.append(self.__DEVICES[cache_key])
            else:
                newDevs.append(None)
        return newDevs

    def name(self) -> str:
        return self._cfg.name

    def scalar_aggregator(self) -> str | None:
        return "tango.pyaml.multi_attribute"

    def vector_aggregator(self) -> str | None:
        return None

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
