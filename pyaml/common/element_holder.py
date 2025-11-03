"""
Module handling element references for simulators and control system
"""
from ..lattice.element import Element
from ..magnet.magnet import Magnet
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter
from ..arrays.magnet_array import MagnetArray
from ..arrays.bpm_array import BPMArray

class ElementHolder(object):
    """
    Class that store references of objects used from both simulators and control system
    """

    def __init__(self):
        # Device handle
        self.__MAGNETS: dict = {}
        self.__BPMS: dict = {}
        self.__RFPLANT: dict = {}
        self.__RFTRANSMITTER: dict = {}
        self.__OTHERS: dict = {}

        # Array handle
        self.__MAGNET_ARRAYS: dict = {}
        self.__BPM_ARRAYS: dict = {}

    def fill_device(self,elements:list[Element]):
       raise "ElementHolder.fill_device() is not subclassed"
    
    # Magnets
    
    def fill_magnet_array(self,arrayName:str,elementNames:list[str]):
       a = []
       for name in elementNames:
          try:
            a.append(self.get_magnet(name))
          except Exception as err:
            raise Exception(f"MagnetArray {arrayName} : {err}")
       self.__MAGNET_ARRAYS[arrayName] = MagnetArray(arrayName,a,self)

    def get_magnet(self,name:str) -> Magnet:
      if name not in self.__MAGNETS:
        raise Exception(f"Magnet {name} not defined")
      return self.__MAGNETS[name]
    
    def add_magnet(self,name:str,m:Magnet):
       self.__MAGNETS[name] = m

    def get_magnets(self,name:str) -> MagnetArray:
       if name not in self.__MAGNET_ARRAYS:
         raise Exception(f"Magnet array {name} not defined")
       return self.__MAGNET_ARRAYS[name]
    
    def get_all_magnets(self) -> dict:
       return self.__MAGNETS

    # BPMs

    def fill_bpm_array(self,arrayName:str,elementNames:list[str]):
       a = []
       for name in elementNames:
          try:
            a.append(self.get_bpm(name))
          except Exception as err:
            raise Exception(f"BpmArray {arrayName} : {err}")
       self.__BPM_ARRAYS[arrayName] = BPMArray(arrayName,a,self)

    def get_bpm(self,name:str) -> Element:
      if name not in self.__BPMS:
         raise Exception(f"BPM {name} not defined")
      return self.__BPMS[name]

    def add_bpm(self,name:str,bpm:Element):
        self.__BPMS[name] = bpm

    def get_bpms(self,name:str) -> BPMArray:
       if name not in self.__BPM_ARRAYS:
         raise Exception(f"BPM array {name} not defined")
       return self.__BPM_ARRAYS[name]

    # RF

    def get_rf_plant(self,name:str) -> RFPlant:
      if name not in self.__RFPLANT:
        raise Exception(f"RFPlant {name} not defined")
      return self.__RFPLANT[name]       

    def add_rf_plant(self,name:str,rf:RFPlant):
       self.__RFPLANT[name] = rf

    def get_rf_plant(self,name:str) -> RFPlant:
      if name not in self.__RFPLANT:
        raise Exception(f"RFPlant {name} not defined")
      return self.__RFPLANT[name]       

    def add_rf_transnmitter(self,name:str,rf:RFTransmitter):
       self.__RFTRANSMITTER[name] = rf

    def get_rf_trasnmitter(self,name:str) -> RFTransmitter:
      if name not in self.__RFTRANSMITTER:
        raise Exception(f"RFTransmitter {name} not defined")
      return self.__RFTRANSMITTER[name]       

    
  
          
