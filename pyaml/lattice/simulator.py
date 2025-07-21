import numpy as np
from pydantic import BaseModel
import at
from ..configuration import get_root_folder
from ..control.element import Element
from pathlib import Path
from ..magnet.magnet import Magnet
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..lattice.abstract_impl import RWCurrentScalar,RWCurrenthArray
from ..lattice.abstract_impl import RWStrengthScalar,RWStrengthArray

# Define the main class name for this module
PYAMLCLASS = "Simulator"

class ConfigModel(BaseModel):

    name: str
    """Simulator name"""
    lattice: str
    """AT lattice file"""
    mat_key: str = None
    """AT lattice ring name"""

class MagnetType:
   HCORRECTOR = 0
   VCORRECTOR = 1
   QUADRUPOLE = 2
   SKEWQUAD = 3
   SEXTUPOLE = 4
   SKEWSEXT = 5
   OCTUPOLE = 6
   SKEWOCTU = 7

_mmap:list = [
    "HCorrector",
    "VCorrector",
    "Quadrupole",
    "SkewQuad",
    "Sextupole",
    "SkewSext",
    "Octupole",
    "SkewOctu"]


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

        # Handle
        self.MAGNETS: list[Element] = {}
        self.DIAGS: list[Element] = {}
        self.RF: list[Element] = {}
        self.OTHERS: list[Element] = {}

    def name(self) -> str:
       return self._cfg.name
    
    def fill_device(self,elements:list[Element]):
       for e in elements:
          if isinstance(e,Magnet):
            current = RWCurrentScalar(self.get_at_elems(e.name),e.polynom,e.unitconv)
            strength = RWStrengthScalar(self.get_at_elems(e.name),e.polynom,e.unitconv)
            # Create a unique ref for this simulator
            m = e.attach(strength,current)
            name = str(m)
            self.MAGNETS[name] = m
          elif isinstance(e,CombinedFunctionMagnet):
            currents = RWCurrenthArray(self.get_at_elems(e.name),e.polynoms,e.unitconv)
            strengths = RWStrengthScalar(self.get_at_elems(e.name),e.polynoms,e.unitconv)
            ms = e.attach(strengths,currents)
            for m in ms:
              name = str(m)
              self.MAGNETS[name] = m
    
    def get_at_elems(self,elementName:str) -> list[at.Element]:
       return [e for e in self.ring if e.FamName == elementName]

    def get_magnet(self,type:MagnetType,name:str) -> Magnet:
      fName = f"{_mmap[type]}({name})"
      if fName not in self.MAGNETS:
        raise Exception(f"Magnet {name} not defined")
      return self.MAGNETS[name]