import os
from pydantic import BaseModel,ConfigDict
from pyaml.control.controlsystem import ControlSystem

PYAMLCLASS : str = "TangoControlSystem"


class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    name: str
    tango_host: str
    debug_level: str=None

class TangoControlSystem(ControlSystem):
    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        print(f"Creating dummy TangoControlSystem: {cfg.name}")

    def name(self) -> str:
        return self._cfg.name

    def init_cs(self):
        pass

    def scalar_aggregator(self) -> str | None:
        return "tango.pyaml.multi_attribute"

    def vector_aggregator(self) -> str | None:
        return None

    def __repr__(self):
       return repr(self._cfg).replace("ConfigModel",self.__class__.__name__)