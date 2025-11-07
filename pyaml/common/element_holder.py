"""
Module handling element references for simulators and control system
"""
from .element import Element
from ..magnet.magnet import Magnet
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..bpm.bpm import BPM
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter
from ..arrays.magnet_array import MagnetArray
from ..arrays.cfm_magnet_array import CombinedFunctionMagnetArray
from ..arrays.bpm_array import BPMArray
from ..arrays.element_array import ElementArray
from ..common.exception import PyAMLException
from ..diagnostics.tune_monitor import BetatronTuneMonitor

class ElementHolder(object):
    """
    Class that store references of objects used from both simulators and control system
    """

    def __init__(self):
        # Device handle
        self.__MAGNETS: dict = {}
        self.__CFM_MAGNETS: dict = {}
        self.__BPMS: dict = {}
        self.__RFPLANT: dict = {}
        self.__RFTRANSMITTER: dict = {}
        self.__DIAG: dict = {}
        self.__ALL: dict = {}

        # Array handle
        self.__MAGNET_ARRAYS: dict = {}
        self.__CFM_MAGNET_ARRAYS: dict = {}
        self.__BPM_ARRAYS: dict = {}
        self.__ELEMENT_ARRAYS: dict = {}

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
       ARR[arrayName] = constructor(arrayName,a)


    def __add(self,array,element:Element):
       if element.get_name() in self.__ALL: # Ensure name unicity
            raise PyAMLException(f"Duplicate element {element.__class__.__name__} name {element.get_name()}") from None
       array[element.get_name()] = element
       self.__ALL[element.get_name()] = element

    def __get(self,what,name,array) -> Element:
       if name not in array:
         raise PyAMLException(f"{what} {name} not defined")
       return array[name]           
    
    # Generic elements
    def fill_element_array(self,arrayName:str,elementNames:list[str]):
      self.fill_array(arrayName,elementNames,self.get_element,ElementArray,self.__ELEMENT_ARRAYS)

    def get_element(self,name:str) -> Element:
       return self.__get("Element",name,self.__ALL)
    
    def get_elemens(self,name:str) -> ElementArray:
       return self.__get("Element array",name,self.__ELEMENT_ARRAYS)

    def get_all_elements(self) -> list[Element]:
       return [value for key, value in self.__ALL.items()]
    
    # Magnets
    
    def fill_magnet_array(self,arrayName:str,elementNames:list[str]):
      self.fill_array(arrayName,elementNames,self.get_magnet,MagnetArray,self.__MAGNET_ARRAYS)

    def get_magnet(self,name:str) -> Magnet:
       return self.__get("Magnet",name,self.__MAGNETS)
    
    def add_magnet(self,m:Magnet):
       self.__add(self.__MAGNETS,m)

    def get_magnets(self,name:str) -> MagnetArray:
       return self.__get("Magnet array",name,self.__MAGNET_ARRAYS)

    def get_all_magnets(self) -> list[Magnet]:
       return [value for key, value in self.__MAGNETS.items()]

    # Combined Function Magnets
    
    def fill_cfm_magnet_array(self,arrayName:str,elementNames:list[str]):
      self.fill_array(arrayName,elementNames,self.get_cfm_magnet,CombinedFunctionMagnetArray,self.__CFM_MAGNET_ARRAYS)

    def get_cfm_magnet(self,name:str) -> Magnet:
       return self.__get("CombinedFunctionMagnet",name,self.__CFM_MAGNETS)
    
    def add_cfm_magnet(self,m:Magnet):
       self.__add(self.__CFM_MAGNETS,m)

    def get_cfm_magnets(self,name:str) -> CombinedFunctionMagnetArray:
       return self.__get("CombinedFunctionMagnet array",name,self.__CFM_MAGNET_ARRAYS)

    def get_all_cfm_magnets(self) -> list[CombinedFunctionMagnet]:
       return [value for key, value in self.__CFM_MAGNETS.items()]
    
    # BPMs

    def fill_bpm_array(self,arrayName:str,elementNames:list[str]):
       self.fill_array(arrayName,elementNames,self.get_bpm,BPMArray,self.__BPM_ARRAYS)

    def get_bpm(self,name:str) -> Element:
      return self.__get("BPM",name,self.__BPMS)

    def add_bpm(self,bpm:BPM):
       self.__add(self.__BPMS,bpm)

    def get_bpms(self,name:str) -> BPMArray:
       return self.__get("BPM array",name,self.__BPM_ARRAYS)

    def get_all_bpms(self) -> list[BPM]:
       return [value for key, value in self.__BPMS.items()]

    # RF

    def get_rf_plant(self,name:str) -> RFPlant:
      return self.__get("RFPlant",name,self.__RFPLANT)

    def add_rf_plant(self,rf:RFPlant):
       self.__add(self.__RFPLANT,rf)

    def add_rf_transnmitter(self,rf:RFTransmitter):
       self.__add(self.__RFTRANSMITTER,rf)

    def get_rf_trasnmitter(self,name:str) -> RFTransmitter:
      return self.__get("RFTransmitter",name,self.__RFTRANSMITTER)


    # Tune monitor  
  
    def get_betatron_tune_monitor(self, name:str) -> BetatronTuneMonitor:
      return self.__get("Diagnostic",name,self.__DIAG)

    def add_betatron_tune_monitor(self, tune_monitor:Element):
        self.__add(self.__DIAG,tune_monitor)
