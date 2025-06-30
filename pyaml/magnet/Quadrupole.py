from .Magnet import Magnet
from .UnitConv import UnitConv
from pyaml.control import Abstract
from pyaml.control.Device import Device
from pyaml.lattice.RWStrengthScalar import RWStrengthScalar
from pyaml.lattice.RWMapper import RWMapper
from pyaml.lattice.RCurrentScalar import RCurrentScalar
from pyaml.configuration.Factory import validate
from typing import Optional

class Quadrupole(Magnet):
    """Quadrupole class"""

    hardware : Optional[Device] = None
    unitconv : Optional[UnitConv] = None

    #@validate
    def __init__(self, **data):
        super().__init__(**data)

        if(self.hardware is not None):
            # TODO
            # Direct access to a magnet device that supports strength/current conversion
            raise Exception("Quadrupole %s, hardware access not implemented" % (self.name))

        # In case of unitconv is none, no control system access possible
        self._strength : Abstract.ReadWriteFloatScalar = RWStrengthScalar(self.name,self.unitconv)
        self._current : Abstract.ReadFloatScalar = RCurrentScalar(self.unitconv)

    """Virtual single function magnet"""
    def setSource(self,source:Abstract.ReadWriteFloatArray,idx:int):
        # Override strength, map single strength to multipole
        self._strength : Abstract.ReadWriteFloatScalar = RWMapper(source,idx)

    def __repr__(self):
        return "%s(name=%s, unitconv=%s)" % (
            self.__class__.__name__, self.name, self.unitconv)

# def factory_constructor(config: dict) -> Quadrupole:
#    """Construct a Quadrupole from Yaml config file"""
#    return Quadrupole(**config)
