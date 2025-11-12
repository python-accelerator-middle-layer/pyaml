"""
Instrument class
"""

from .control.controlsystem import ControlSystem
from .common.element import Element
from .lattice.simulator import Simulator
from .arrays.array import ArrayConfig
from pydantic import BaseModel,ConfigDict

# Define the main class name for this module
PYAMLCLASS = "Instrument"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    name: str
    """Instrument name"""
    energy: float
    """Instrument nominal energy, for ramped machine, this value can be dynamically set"""
    controls: list[ControlSystem] = None
    """List of control system used, an instrument can access several control systems"""
    simulators: list[Simulator] = None
    """Simulator list"""
    data_folder: str
    """Data folder"""
    arrays: list[ArrayConfig] = None
    """Element family"""
    devices: list[Element]
    """Element list"""


class Instrument(object):    
    """PyAML top level class"""
    
    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        __design = None
        __live = None

        if cfg.controls is not None:
            for c in cfg.controls:
                if c.name() == "live":
                  self.__live = c
                else:
                  # Add as dynacmic attribute
                  setattr(self,c.name(),c)
                c.init_cs()
                c.fill_device(cfg.devices)

        if cfg.simulators is not None:
            for s in cfg.simulators:
                if s.name() == "design":
                  self.__design = s
                else:
                  # Add as dynacmic attribute
                  setattr(self,s.name(),s)
                s.fill_device(cfg.devices)

        if cfg.arrays is not None:
            for a in cfg.arrays:
                if cfg.simulators is not None:
                    for s in cfg.simulators:
                        a.fill_array(s)
                if cfg.controls is not None:
                    for c in cfg.controls:
                        a.fill_array(c)

        if cfg.energy is not None:
            self.set_energy(cfg.energy)

    def set_energy(self,E:float):
        if self._cfg.simulators is not None:
            for s in self._cfg.simulators:
                s.set_energy(E)
        if self._cfg.controls is not None:
            for c in self._cfg.controls:
                c.set_energy(E)

    @property
    def live(self) -> ControlSystem:
        return self.__live

    @property
    def design(self) -> Simulator:
        return self.__design
