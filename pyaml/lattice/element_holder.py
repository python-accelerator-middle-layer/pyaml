"""
Module handling element references for simulators and control system
"""
from .element import Element
from ..magnet.magnet import Magnet
from ..arrays.magnet_array import MagnetArray

class MagnetType:
   COMBINED = 0
   HCORRECTOR = 1
   VCORRECTOR = 2
   QUADRUPOLE = 3
   SKEWQUAD = 4
   SEXTUPOLE = 5
   SKEWSEXT = 6
   OCTUPOLE = 7
   SKEWOCTU = 8

_mmap:list = [
    "CombinedFunctionMagnet",
    "HCorrector",
    "VCorrector",
    "Quadrupole",
    "SkewQuad",
    "Sextupole",
    "SkewSext",
    "Octupole",
    "SkewOctu"]


class ElementHolder(object):
    """
    Class that store references of objects used from both simulators and control system
    """

    def __init__(self):
        # Device handle
        self.MAGNETS: dict = {}
        self.BPMS: dict = {}
        self.RF: dict = {}
        self.OTHERS: dict = {}

        # Array handle
        self.MAGNET_ARRAYS: dict = {}
    
    def fill_device(self,elements:list[Element]):
       raise "ElementHolder.fill_device() is not subclassed"
    
    def fill_magnet_array(self,type:MagnetType,arrayName:str,elementNames:list[str]):
       a = []
       for name in elementNames:
          try:
            a.append(self.get_magnet(type,name))
          except Exception as err:
            raise Exception(f"MagnetArray {arrayName} : {err}")
       self.MAGNET_ARRAYS[arrayName] = MagnetArray(a)

    def get_magnet(self,type:MagnetType,name:str) -> Magnet:
      fName = f"{_mmap[type]}({name})"
      if fName not in self.MAGNETS:
        raise Exception(f"Magnet {fName} not defined")
      return self.MAGNETS[fName]
    
    def get_magnets(self,name:str) -> MagnetArray:
       if name not in self.MAGNET_ARRAYS:
         raise Exception(f"Magnet array {name} not defined")
       return self.MAGNET_ARRAYS[name]
          