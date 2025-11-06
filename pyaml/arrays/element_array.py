from ..common.element import Element
from ..magnet.magnet import Magnet
from ..bpm.bpm import BPM
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..common.exception import PyAMLException

import importlib
import fnmatch

class ElementArray(list[Element]):
    """
    Class that implements access to a element array
    """

    def __init__(self,arrayName:str,elements:list[Element],use_aggregator = True):
        """
        Construct an element array

        Parameters
        ----------
        arrayName : str
            Array name
        elements: list[Element]
            Element list, all elements must be attached to the same instance of 
            either a Simulator or a ControlSystem.
        use_aggregator : bool
            Use aggregator to increase performance by using paralell access to underlying devices.
        """
        super().__init__(i for i in elements)
        self.__name = arrayName
        self.__peer = self[0]._peer if len(self)>0 else None
        self.__use_aggretator = use_aggregator
        if self.__peer is None or any([m._peer!=self.__peer for m in self]):
            raise PyAMLException(f"{self.__class__.__name__} {self.get_name()}:  All elements must be attached to the same instance of either a Simulator or a ControlSystem")

    def get_peer(self):
        """
        Returns the peer (Simulator or ControlSystem) of an element list
        """
        return self.__peer

    def get_name(self) -> str:
        return self.__name

    def names(self) -> list[str]:
        return [e.get_name() for e in self]
        
    def __create_array(self,arrName:str,eltType:type,elements:list):

        if len(elements)==0:
            return []

        if issubclass(eltType,Magnet):
            m = importlib.import_module("pyaml.arrays.magnet_array")
            arrayClass =  getattr(m, "MagnetArray", None)
            return arrayClass("",elements,self.__use_aggretator)
        elif issubclass(eltType,BPM):
            m = importlib.import_module("pyaml.arrays.bpm_array")
            arrayClass =  getattr(m, "BPMArray", None)
            return arrayClass("",elements,self.__use_aggretator)
        elif issubclass(eltType,CombinedFunctionMagnet):
            m = importlib.import_module("pyaml.arrays.cfm_magnet_array")
            arrayClass =  getattr(m, "CombinedFunctionMagnetArray", None)
            return arrayClass("",elements,self.__use_aggretator)
        elif issubclass(eltType,Element):
            return ElementArray("",elements,self.__use_aggretator)
        else:
            raise PyAMLException(f"Unsupported sliced array for type {str(eltType)}")
        
    def __eval_field(self,attName:str,e:Element) -> str:
        funcName = "get_" + attName
        func = getattr(e,funcName, None)
        return func() if func is not None else ""

    def __getitem__(self,key):

        if isinstance(key,slice):

            # Slicing
            eltType = None
            r = []
            for i in range(*key.indices(len(self))):
                if eltType is None:
                    eltType = type(self[i])
                elif not isinstance(self[i],eltType):
                    eltType = Element # Fall back to element
                r.append(self[i])
            return self.__create_array("",eltType,r)

        elif isinstance(key,str):

            fields = key.split(':')

            if len(fields)<=1:
                # Selection by name
                eltType = None
                r = []
                for e in self:
                    if fnmatch.fnmatch(e.get_name(), key):
                        if eltType is None:
                            eltType = type(e)
                        elif not isinstance(e,eltType):
                            eltType = Element # Fall back to element
                        r.append(e)
            else:
                # Selection by fields
                eltType = None
                r = []
                for e in self:
                    txt = self.__eval_field(fields[0],e)
                    if fnmatch.fnmatch(txt , fields[1]):
                        if eltType is None:
                            eltType = type(e)
                        elif not isinstance(e,eltType):
                            eltType = Element # Fall back to element
                        r.append(e)

            return self.__create_array("",eltType,r)

        else:
            # Default to super selection
            return super().__getitem__(key)
