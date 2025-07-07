import numpy as np
from pydantic import BaseModel
from ..configuration.factory import get_element
from ..lattice.abstract_impl import RWStrengthArrayFamily
from ..control import abstract

# Define the main class name for this module
PYAMLCLASS = "Array"

class ConfigModel(BaseModel):

    name: str
    """Family name"""
    elements: list[str]
    """List of pyaml element names"""

class Array(object):
    """
    Class that implements access to arrays (families)
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

    def fill(self,parent):
        self.elements = []
        for e in self._cfg.elements:
            try:
                self.elements.append(get_element(e))
            except Exception as ex:
                raise Exception(f"Array {self._cfg.name}: {e} element not found")

        self.strength: abstract.ReadWriteFloatArray = RWStrengthArrayFamily(self.elements)
        setattr(parent,self._cfg.name,self)
            
        
