from .Magnet import Magnet
from .UnitConv import UnitConv
from pyaml.control import Abstract
from pyaml.control.Device import Device
from pyaml.lattice.RWFloat import RWFloat
from pyaml.configuration.Factory import validate

class Quadrupole(Magnet):
    """Quadrupole class"""
    @validate
    def __init__(self, name:str, hardware:Device = None, unitconv: UnitConv = None):
        super().__init__(name)

        if(hardware is not None):
            # Direct access to a magnet device that supports strength/current conversion
            # TODO
            raise Exception("Quadrupole %s, hardware access not implemented" % (name))
        elif(unitconv is not None):
            self.unitconv = unitconv
        else:
            raise Exception("Quadrupole %s, no control system or model defined" % (name))

        self.strength : Abstract.ReadWriteFloatScalar = RWFloat(self.unitconv)

    def __repr__(self):
        return "%s(name=%s, unitconv=%s)" % (
            self.__class__.__name__, self.name, self.unitconv)

def factory_constructor(config: dict) -> Quadrupole:
   """Construct a Quadrupole from Yaml config file"""
   return Quadrupole(**config)
