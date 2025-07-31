import os
from pydantic import BaseModel,ConfigDict
from pyaml.control.controlsystem import ControlSystem

PYAMLCLASS : str = "TangoControlSystem"


class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    name: str
    tango_host: str
    debug_level: int


class TangoControlSystem(ControlSystem):
    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg

    def name(self) -> str:
        return self._cfg.name

    def init_cs(self):
        pass
