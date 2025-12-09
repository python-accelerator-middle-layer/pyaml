import copy
import os

from pydantic import BaseModel, ConfigDict

from pyaml.control.controlsystem import ControlSystem
from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS: str = "TangoControlSystem"

DEVICES = {}


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    tango_host: str
    debug_level: str = None


class TangoControlSystem(ControlSystem):
    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        print(f"Creating dummy TangoControlSystem: {cfg.name}")

    def attach(self, devs: list[DeviceAccess]) -> list[DeviceAccess]:
        global DEVICES
        newDevs = []
        for d in devs:
            if d is not None:
                full_name = "//" + self._cfg.tango_host + "/" + d._cfg.attribute
                if full_name not in DEVICES:
                    # Shallow copy the object
                    newDev = copy.copy(d)
                    # Shallow copy the config object
                    # to allow a new attribute name
                    newDev._cfg = copy.copy(d._cfg)
                    newDev._cfg.attribute = full_name
                    DEVICES[full_name] = newDev
                newDevs.append(DEVICES[full_name])
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
