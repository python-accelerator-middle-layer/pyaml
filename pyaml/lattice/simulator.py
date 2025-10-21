from pydantic import BaseModel,ConfigDict
import at

from .attribute_linker import PyAtAttributeElementsLinker, ConfigModel as PyAtAttrLinkerConfigModel
from .lattice_elements_linker import LatticeElementsLinker
from ..configuration import get_root_folder
from .element import Element
from pathlib import Path
from ..magnet.magnet import Magnet
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..rf.rf_plant import RFPlant,RWTotalVoltage
from ..rf.rf_transmitter import RFTransmitter
from ..lattice.abstract_impl import RWHardwareScalar,RWHardwareArray
from ..lattice.abstract_impl import RWStrengthScalar,RWStrengthArray
from ..lattice.abstract_impl import RWRFFrequencyScalar,RWRFVoltageScalar,RWRFPhaseScalar
from .element_holder import ElementHolder

# Define the main class name for this module
PYAMLCLASS = "Simulator"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    name: str
    """Simulator name"""
    lattice: str
    """AT lattice file"""
    mat_key: str = None
    """AT lattice ring name"""
    linker: LatticeElementsLinker = None
    """The linker configuration model"""

class Simulator(ElementHolder):
    """
    Class that implements access to AT simulator
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        self._linker = cfg.linker if cfg.linker else PyAtAttributeElementsLinker(PyAtAttrLinkerConfigModel(attribute_name="FamName"))
        path:Path = get_root_folder() / cfg.lattice

        if(self._cfg.mat_key is None):
          self.ring = at.load_lattice(path)
        else:
          self.ring = at.load_lattice(path,mat_key=f"{self._cfg.mat_key}")

        self._linker.set_lattice(self.ring)

    def name(self) -> str:
       return self._cfg.name
    
    def get_lattice(self) -> at.Lattice:
      return self.ring
    
    def set_energy(self,E:float):
      self.ring.energy = E
      # For current calculation
      for m in self.get_all_magnets().items():
        m[1].set_energy(E)
    
    def fill_device(self,elements:list[Element]):
       for e in elements:
          # Need conversion to physics unit to work with simulator
          if isinstance(e,Magnet):
            current = RWHardwareScalar(self.get_at_elems(e),e.polynom,e.model) if e.model.has_physics() else None
            strength = RWStrengthScalar(self.get_at_elems(e),e.polynom,e.model) if e.model.has_physics() else None
            # Create a unique ref for this simulator
            m = e.attach(strength,current)
            self.add_magnet(m.get_name(),m)

          elif isinstance(e,CombinedFunctionMagnet):
            self.add_magnet(e.get_name(),e)
            currents = RWHardwareArray(self.get_at_elems(e),e.polynoms,e.model) if e.model.has_physics() else None
            strengths = RWStrengthArray(self.get_at_elems(e),e.polynoms,e.model) if e.model.has_physics() else None
            # Create unique refs of each function for this simulator
            ms = e.attach(strengths,currents)
            for m in ms:
              self.add_magnet(m.get_name(),m)
              self.add_magnet(m.get_name(),m)

          elif isinstance(e,RFPlant):
             self.add_rf_plant(e.get_name(),e)
             cavs: list[at.Element] = []
             harmonics: list[float] = []
             attachedTrans: list[RFTransmitter] = []
             for t in e._cfg.transmitters:
                cavsPerTrans: list[at.Element] = []
                for c in t._cfg.cavities:
                   # Expect unique name for cavities
                   cav = self.get_at_elems(Element(c))
                   if len(cav)>1:
                         raise Exception(f"RF transmitter {t.get_name()}, multiple cavity definition:{cav[0]}")
                   if len(cav)==0:
                         raise Exception(f"RF transmitter {t.get_name()}, No cavity found")
                   cavsPerTrans.append(cav[0])
                   harmonics.append(t._cfg.harmonic)

                voltage = RWRFVoltageScalar(cavsPerTrans,t)
                phase = RWRFPhaseScalar(cavsPerTrans,t)
                nt = t.attach(voltage,phase)
                attachedTrans.append(nt)
                self.add_rf_transnmitter(nt.get_name(),nt)
                cavs.extend(cavsPerTrans)

             frequency = RWRFFrequencyScalar(cavs,harmonics,e)
             voltage = RWTotalVoltage(attachedTrans)
             ne = e.attach(frequency,voltage)
             self.add_rf_plant(ne.get_name(),ne)
             
    
    def get_at_elems(self,element:Element) -> list[at.Element]:
       identifier = self._linker.get_element_identifier(element)
       element_list = self._linker.get_at_elements(identifier)
       if not element_list:
          raise Exception(f"{identifier} not found in lattice:{self._cfg.lattice}")
       return element_list
