"""
Instrument class
"""

from .control.controlsystem import ControlSystem
from .lattice.element import Element
from .lattice.simulator import Simulator
from .arrays.array import Array
from pydantic import BaseModel,ConfigDict

# Define the main class name for this module
PYAMLCLASS = "Instrument"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    """Instrument name"""
    energy: float = None
    """Instrument nominal energy, for ramped machine, this value can be dynamically set"""
    control: list[ControlSystem] = None
    """List of control system used, an instrument can access sevral control system"""
    simulators: list[Simulator] = None
    """Simulator list"""
    data_folder: str
    """Data folder"""
    arrays: list[Array] = None
    """Element family"""
    devices: list[Element]
    """Element list"""


class Instrument(object):    
    """PyAML top level class"""
    
    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        __design = None
        __live = None

        if cfg.control is not None:
            for c in cfg.control:
                if c.name() == "live":
                    self.__live = c
                    c.init_cs()

        if cfg.simulators is not None:
            for s in cfg.simulators:
                if s.name() == "design":
                  self.__design = s
                s.fill_device(cfg.devices)

        if cfg.arrays is not None:
            for a in cfg.arrays:                    
                for s in cfg.simulators:
                    a.fill_array(s)

        if cfg.energy is not None:
            self.set_energy(cfg.energy)

    def set_energy(self,E:float):
        if self._cfg.simulators is not None:
            for s in self._cfg.simulators:
                s.set_energy(E)
        # TODO: apply E on Control system

    @property
    def live(self) -> ControlSystem:
        return self.__live

    @property
    def design(self) -> Simulator:
        return self.__design
