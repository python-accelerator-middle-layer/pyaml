import numpy as np
from pydantic import BaseModel
from ..configuration.factory import get_element
from ..lattice.abstract_impl import RWStrengthArrayFamily
from ..control import abstract
from ..control.controlsystem import ControlSystem
from ..lattice.simulator import Simulator


class ArrayModel(BaseModel):

    name: str
    """Family name"""
    elements: list[str]
    """List of pyaml element names"""

class Array(object):
    """
    Class that implements access to arrays (families)
    """

    def __init__(self, cfg: ArrayModel):
        self._cfg = cfg

    def fill(self):
        self.elements = []
        className = self.__class__.__name__
        for e in self._cfg.elements:
            objectName = f"{className}({e})"
            try:
                self.elements.append(get_element(objectName))
            except Exception as ex:
                raise Exception(f"Array {self._cfg.name}: {objectName} element not found")

    def attach_cs(self,parent,cs:ControlSystem):
        self.strength: abstract.ReadWriteFloatArray = RWStrengthArrayFamily(self.elements,cs)
        setattr(cs,self._cfg.name,self)
        setattr(parent,cs.name(),cs)

    def attach_model(self,parent,model:Simulator):
        self.strength: abstract.ReadWriteFloatArray = RWStrengthArrayFamily(self.elements,model)
        setattr(model,self._cfg.name,self)
        setattr(parent,model.name(),model)


            
        
