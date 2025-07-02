from pydantic import BaseModel

from ..control import abstract
from ..control.deviceaccess import DeviceAccess
from ..lattice.abstract_impl import RWStrengthScalar
from ..lattice.abstract_impl import RWMapper
from ..lattice.abstract_impl import RCurrentScalar
from .magnet import Magnet
from .unitconv import UnitConv

# Define the main class name for this module
PYAMLCLASS = "Quadrupole"

class ConfigModel(BaseModel):

    """Element name"""
    name : str
    """Direct access to a magnet device that provides strength/current conversion"""
    hardware: DeviceAccess | None = None
    """Object in charge of converting magnet strenghts to current"""
    unitconv: UnitConv | None = None

class Quadrupole(Magnet):
    
    """Quadrupole class"""

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg
        self.unitconv = cfg.unitconv

        if cfg.hardware is not None:
            # TODO
            # Direct access to a magnet device that supports strength/current conversion
            raise Exception(
                "Quadrupole %s, hardware access not implemented" % (cfg.name)
            )
        
        # In case of unitconv is none, no control system access possible
        self.strength: abstract.ReadWriteFloatScalar = RWStrengthScalar(
            cfg.name, self.unitconv
        )
        self.current: abstract.ReadFloatScalar = RCurrentScalar(self.unitconv)

    """Virtual single function magnet"""

    def setSource(self, source: abstract.ReadWriteFloatArray, idx: int):
        # Override strength, map single strength to multipole
        self.strength: abstract.ReadWriteFloatScalar = RWMapper(source, idx)

    def __repr__(self):
        return "%s(name=%s, unitconv=%s)" % (
            self.__class__.__name__,
            self.name,
            self.unitconv,
        )
