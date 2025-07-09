import numpy as np
from pydantic import BaseModel
import at
from ..configuration import get_root_folder
from pathlib import Path

# Define the main class name for this module
PYAMLCLASS = "Simulator"

class ConfigModel(BaseModel):

    name: str
    """Simulator name"""
    lattice: str
    """AT lattice file"""
    mat_key: str = None
    """AT lattice ring name"""

class Simulator(object):
    """
    Class that implements access to AT simulator
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        path:Path = get_root_folder() / cfg.lattice

        if(self._cfg.mat_key is None):
          self.ring = at.load_lattice(path)
        else:
          self.ring = at.load_lattice(path,mat_key=f"{self._cfg.mat_key}")

    def name(self) -> str:
       return self._cfg.name

    def get_elems(self,elementName:str) -> list:
       # Create a list of elements having the same FamName
       ring = [e for e in self.ring if e.FamName == elementName]
        #Get element
        #elem = [e for e in lattice if e.Device == elementName]
        #if not elem:
        #    raise ValueError(f"{elementName} not found")
        #if len(elem) != 1:
        #    raise ValueError(f"{elementName} is not unique")
        #if not hasattr(elem[0],attrName):
        #    raise ValueError(f"{elementName} has no field {attrName}")
        #self._element = elem
        #self._attr = attrName

