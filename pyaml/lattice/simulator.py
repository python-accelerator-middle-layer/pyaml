from pydantic import BaseModel
import at
from ..configuration import get_root_folder
from .element import Element
from pathlib import Path
from ..magnet.magnet import Magnet
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..lattice.abstract_impl import RWHardwareScalar,RWHardwareArray
from ..lattice.abstract_impl import RWStrengthScalar,RWStrengthArray
from .element_holder import ElementHolder

# Define the main class name for this module
PYAMLCLASS = "Simulator"

class ConfigModel(BaseModel):

    name: str
    """Simulator name"""
    lattice: str
    """AT lattice file"""
    mat_key: str = None
    """AT lattice ring name"""

class Simulator(ElementHolder):
    """
    Class that implements access to AT simulator
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        path:Path = get_root_folder() / cfg.lattice

        if(self._cfg.mat_key is None):
          self.ring = at.load_lattice(path)
        else:
          self.ring = at.load_lattice(path,mat_key=f"{self._cfg.mat_key}")

    def name(self) -> str:
       return self._cfg.name
    
    def get_lattice(self) -> at.Lattice:
      return self.ring
    
    def set_energy(self,E:float):
      self.ring.energy = E
      # For current calculation
      for m in self.MAGNETS.items():
        m[1].set_energy(E)
    
    def fill_device(self,elements:list[Element]):
       for e in elements:
          if isinstance(e,Magnet):
            current = RWHardwareScalar(self.get_at_elems(e.name),e.polynom,e.model)
            strength = RWStrengthScalar(self.get_at_elems(e.name),e.polynom,e.model)
            # Create a unique ref for this simulator
            m = e.attach(strength,current)
            name = str(m)
            self.MAGNETS[name] = m
          elif isinstance(e,CombinedFunctionMagnet):
            self.MAGNETS[str(e)]=e
            currents = RWHardwareArray(self.get_at_elems(e.name),e.polynoms,e.model)
            strengths = RWStrengthArray(self.get_at_elems(e.name),e.polynoms,e.model)
            # Create unique refs of each function for this simulator
            ms = e.attach(strengths,currents)
            for m in ms:
              self.MAGNETS[str(m)] = m
    
    def get_at_elems(self,elementName:str) -> list[at.Element]:
       elementList = [e for e in self.ring if e.FamName == elementName]
       if not elementList:
          raise Exception(f"{elementName} not found in lattice:{self._cfg.lattice}")
       return elementList
