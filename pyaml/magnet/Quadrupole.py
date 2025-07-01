from pydantic import SerializeAsAny
from pydantic import BaseModel

from .UnitConv import UnitConv
from ..control import Abstract
from ..control.DeviceAccess import DeviceAccess
from ..lattice.RWStrengthScalar import RWStrengthScalar
from ..lattice.RWMapper import RWMapper
from ..lattice.RCurrentScalar import RCurrentScalar
from .Magnet import Magnet

class Config(BaseModel):

    name : str
    hardware: SerializeAsAny[DeviceAccess] | None = None
    unitconv: SerializeAsAny[UnitConv] | None = None
    

class Quadrupole(Magnet):
    
    """Quadrupole class"""

    def __init__(self, cfg: Config):
        super().__init__(cfg.name)

        self.unitconv = cfg.unitconv

        if cfg.hardware is not None:
            # TODO
            # Direct access to a magnet device that supports strength/current conversion
            raise Exception(
                "Quadrupole %s, hardware access not implemented" % (cfg.name)
            )
        
        # In case of unitconv is none, no control system access possible
        self.strength: Abstract.ReadWriteFloatScalar = RWStrengthScalar(
            cfg.name, self.unitconv
        )
        self.current: Abstract.ReadFloatScalar = RCurrentScalar(self.unitconv)

    """Virtual single function magnet"""

    def setSource(self, source: Abstract.ReadWriteFloatArray, idx: int):
        # Override strength, map single strength to multipole
        self.strength: Abstract.ReadWriteFloatScalar = RWMapper(source, idx)

    def __repr__(self):
        return "%s(name=%s, unitconv=%s)" % (
            self.__class__.__name__,
            self.name,
            self.unitconv,
        )
