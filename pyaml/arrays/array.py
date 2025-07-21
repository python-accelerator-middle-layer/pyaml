import numpy as np
from pydantic import BaseModel
from ..configuration.factory import get_element


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
            elemName = f"{className}({e})"
            elem = None
            try:
                elem = get_element(elemName)
            except Exception as ex:
                raise Exception(f"Array {self._cfg.name}: {elemName} element not found")
            if elem in self.elements:
                raise Exception(f"Array {self._cfg.name}: {elemName} already referenced in array")
            self.elements.append(elem)


            
        
