"""
Module handling element references for simulators and control system
"""
from .element import Element
from ..magnet.magnet import Magnet
from ..arrays.magnet_array import MagnetArray


class ElementHolder(object):
    """
    Class that store references of objects used from both simulators and control system
    """

    def __init__(self):
        # Device handle
        self.__MAGNETS: dict = {}
        self.__BPMS: dict = {}
        self.__RF: dict = {}
        self.__OTHERS: dict = {}

        # Array handle
        self.__MAGNET_ARRAYS: dict = {}
    
    def fill_device(self,elements:list[Element]):
       raise "ElementHolder.fill_device() is not subclassed"
    
    def fill_magnet_array(self,arrayName:str,elementNames:list[str]):
       a = []
       for name in elementNames:
          try:
            a.append(self.get_magnet(name))
          except Exception as err:
            raise Exception(f"MagnetArray {arrayName} : {err}")
       self.__MAGNET_ARRAYS[arrayName] = MagnetArray(arrayName,a)

    def get_magnet(self,name:str) -> Magnet:
      if name not in self.__MAGNETS:
        raise Exception(f"Magnet {name} not defined")
      return self.__MAGNETS[name]
    
    def add_magnet(self,name:str,m:Magnet):
        self.__MAGNETS[name] = m

    def get_all_magnets(self) -> dict:
       return self.__MAGNETS
    
    def get_magnets(self,name:str) -> MagnetArray:
       if name not in self.__MAGNET_ARRAYS:
         raise Exception(f"Magnet array {name} not defined")
       return self.__MAGNET_ARRAYS[name]
          