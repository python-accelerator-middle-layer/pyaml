"""
Module handling element references for simulators and control system
"""
from .element import Element
from ..magnet.magnet import Magnet
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter
from ..arrays.magnet_array import MagnetArray
from ..arrays.bpm_array import BPMArray
from ..common.exception import PyAMLException

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
        self.__DIAG: dict = {}

        # Array handle
        self.__MAGNET_ARRAYS: dict = {}
        self.__BPM_ARRAYS: dict = {}

    def fill_device(self,elements:list[Element]):
       raise "ElementHolder.fill_device() is not subclassed"
    
    def fill_array(self,arrayName:str,elementNames:list[str],get_func,constructor,ARR:dict):
       a = []
       for name in elementNames:
          try:
            m = get_func(name)
          except Exception as err:
            raise PyAMLException(f"{constructor.__name__} {arrayName} : {err} @index {len(a)}") from None
          if m in a:
            raise PyAMLException(f"{constructor.__name__} {arrayName} : duplicate name {name} @index {len(a)}") from None             
          a.append(m)          
       ARR[arrayName] = constructor(arrayName,a,self)
    
    # Magnets
    
    def fill_magnet_array(self,arrayName:str,elementNames:list[str]):
       self.fill_array(arrayName,elementNames,self.get_magnet,MagnetArray,self.__MAGNET_ARRAYS)

    def get_magnet(self,name:str) -> Magnet:
      if name not in self.__MAGNETS:
        raise PyAMLException(f"Magnet {name} not defined")
      return self.__MAGNETS[name]
    
    def add_magnet(self,name:str,m:Magnet):
       if name in self.__MAGNETS:
            print(self.__MAGNETS)
            raise PyAMLException(f"Duplicate magnet name {name}") from None
       self.__MAGNETS[name] = m

    def get_magnets(self,name:str) -> MagnetArray:
       if name not in self.__MAGNET_ARRAYS:
         raise PyAMLException(f"Magnet array {name} not defined")
       return self.__MAGNET_ARRAYS[name]
    
    def get_all_magnets(self) -> dict:
       return self.__MAGNETS

    # BPMs

    def fill_bpm_array(self,arrayName:str,elementNames:list[str]):
       self.fill_array(arrayName,elementNames,self.get_bpm,BPMArray,self.__BPM_ARRAYS)

    def get_bpm(self,name:str) -> Element:
      if name not in self.__BPMS:
         raise PyAMLException(f"BPM {name} not defined")
      return self.__BPMS[name]

    def add_bpm(self,name:str,bpm:Element):
        self.__BPMS[name] = bpm

    def get_bpms(self,name:str) -> BPMArray:
       if name not in self.__BPM_ARRAYS:
         raise PyAMLException(f"BPM array {name} not defined")
       return self.__BPM_ARRAYS[name]

    # RF

    def get_rf_plant(self,name:str) -> RFPlant:
      if name not in self.__RFPLANT:
        raise PyAMLException(f"RFPlant {name} not defined")
      return self.__RFPLANT[name]       

    def add_rf_plant(self,name:str,rf:RFPlant):
       self.__RFPLANT[name] = rf

    def get_rf_plant(self,name:str) -> RFPlant:
      if name not in self.__RFPLANT:
        raise PyAMLException(f"RFPlant {name} not defined")
      return self.__RFPLANT[name]       

    def add_rf_transnmitter(self,name:str,rf:RFTransmitter):
       self.__RFTRANSMITTER[name] = rf

    def get_rf_trasnmitter(self,name:str) -> RFTransmitter:
      if name not in self.__RFTRANSMITTER:
        raise PyAMLException(f"RFTransmitter {name} not defined")
      return self.__RFTRANSMITTER[name]       

    
  
    def get_bpm(self,name:str) -> Element:
      if name not in self.__BPMS:
         raise Exception(f"BPM {name} not defined")
      return self.__BPMS[name]

    def add_bpm(self,name:str,bpm:Element):
        self.__BPMS[name] = bpm

    def get_betatron_tune_monitor(self, name:str) -> Element:
        if name not in self.__DIAG:
            raise Exception(f"Diagnostic devices array does not contain {name}")
        return self.__DIAG[name]

    def add_betatron_tune_monitor(self, name:str, tune_monitor:Element):
        self.__DIAG[name] = tune_monitor
