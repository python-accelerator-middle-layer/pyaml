from .Magnet import Magnet
from .UnitConv import UnitConv
from pyaml.control import Abstract
from pyaml.control.Device import Device
from pyaml.lattice.RWStrengthScalar import RWStrengthScalar
from pyaml.lattice.RWMapper import RWMapper
from pyaml.lattice.RCurrentScalar import RCurrentScalar
from pyaml.configuration.Factory import validate

class Quadrupole(Magnet):
    """Quadrupole class"""
    @validate
    def __init__(self, name:str, hardware:Device = None, unitconv: UnitConv = None):
        super().__init__(name)

        self.unitconv = None
        
        if hardware is not None:
            # TODO
            # Direct access to a magnet device that supports strength/current conversion
            raise Exception("Quadrupole %s, hardware access not implemented" % (name))
        else:
            # In case of unitconv is none, no control system access possible
            self.unitconv = unitconv

        self.strength : Abstract.ReadWriteFloatScalar = RWStrengthScalar(name,self.unitconv)
        self.current : Abstract.ReadFloatScalar = RCurrentScalar(self.unitconv)

    """Virtual single function magnet"""
    def setSource(self,source:Abstract.ReadWriteFloatArray,idx:int):
        # Override strength, map single strength to multipole
        self.strength : Abstract.ReadWriteFloatScalar = RWMapper(source,idx)

    def __repr__(self):
        return "%s(name=%s, unitconv=%s)" % (
            self.__class__.__name__, self.name, self.unitconv)

def factory_constructor(config: dict) -> Quadrupole:
   """Construct a Quadrupole from Yaml config file"""
   return Quadrupole(**config)
