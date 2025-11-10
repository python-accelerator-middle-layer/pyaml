from .attribute_linker import PyAtAttributeElementsLinker, ConfigModel as PyAtAttrLinkerConfigModel
from .lattice_elements_linker import LatticeElementsLinker
from ..configuration import get_root_folder
from ..common.element import Element
from ..magnet.magnet import Magnet
from ..bpm.bpm import BPM
from ..diagnostics.tune_monitor import BetatronTuneMonitor
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..rf.rf_plant import RFPlant,RWTotalVoltage
from ..rf.rf_transmitter import RFTransmitter
from ..lattice.abstract_impl import RWHardwareScalar,RWHardwareArray
from ..lattice.abstract_impl import RWStrengthScalar,RWStrengthArray
from ..lattice.abstract_impl import RWRFFrequencyScalar,RWRFVoltageScalar,RWRFPhaseScalar
from ..lattice.abstract_impl import RWRFATFrequencyScalar,RWRFATotalVoltageScalar
from ..common.element_holder import ElementHolder
from ..common.abstract_aggregator import ScalarAggregator
from ..lattice.abstract_impl import RBetatronTuneArray
from ..lattice.abstract_impl import RWBpmTiltScalar,RWBpmOffsetArray, RBpmArray
from ..lattice.abstract_impl import BPMHScalarAggregator,BPMScalarAggregator,BPMVScalarAggregator
from ..common.exception import PyAMLException

from pydantic import BaseModel,ConfigDict
import at
from pathlib import Path

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
      # Needed by energy dependant element (i.e. magnet coil current calculation)
      for m in self.get_all_elements():
        m.set_energy(E)
 
    def create_magnet_strength_aggregator(self,magnets:list[Magnet]) -> ScalarAggregator:
        # No magnet aggregator for simulator
        return None
 
    def create_magnet_harddware_aggregator(self,magnets:list[Magnet]) -> ScalarAggregator:
        # No magnet aggregator for simulator
        return None

    def create_bpm_aggregators(self,bpms:list[BPM]) -> list[ScalarAggregator]:
        agg = BPMScalarAggregator(self.get_lattice())
        aggh = BPMHScalarAggregator(self.get_lattice())
        aggv = BPMVScalarAggregator(self.get_lattice())
        for b in bpms:
          e = self.get_at_elems(b)[0]
          agg.add_elem(e)
          aggh.add_elem(e)
          aggv.add_elem(e)
        return [agg,aggh,aggv]
    
    def fill_device(self,elements:list[Element]):
       for e in elements:
          # Need conversion to physics unit to work with simulator
          if isinstance(e,Magnet):
            current = RWHardwareScalar(self.get_at_elems(e),e.polynom,e.model) if e.model.has_physics() else None
            strength = RWStrengthScalar(self.get_at_elems(e),e.polynom,e.model) if e.model.has_physics() else None
            # Create a unique ref for this simulator
            m = e.attach(self,strength,current)
            self.add_magnet(m)

          elif isinstance(e,CombinedFunctionMagnet):
            currents = RWHardwareArray(self.get_at_elems(e),e.polynoms,e.model) if e.model.has_physics() else None
            strengths = RWStrengthArray(self.get_at_elems(e),e.polynoms,e.model) if e.model.has_physics() else None
            # Create unique refs of each function for this simulator
            ms = e.attach(self,strengths,currents)
            self.add_cfm_magnet(ms[0])
            for m in ms[1:]:
              self.add_magnet(m)
              
          elif isinstance(e,BPM):
            # This assumes unique BPM names in the pyAT lattice  
            tilt = RWBpmTiltScalar(self.get_at_elems(e)[0])
            offsets = RWBpmOffsetArray(self.get_at_elems(e)[0])
            positions = RBpmArray(self.get_at_elems(e)[0],self.ring)
            e = e.attach(self,positions, offsets, tilt)
            self.add_bpm(e)

          elif isinstance(e,RFPlant):
            if e._cfg.transmitters:
              cavs: list[at.Element] = []
              harmonics: list[float] = []
              attachedTrans: list[RFTransmitter] = []
              for t in e._cfg.transmitters:
                cavsPerTrans: list[at.Element] = []
                for c in t._cfg.cavities:
                  # Expect unique name for cavities
                  cav = self.get_at_elems(Element(c))
                  if len(cav)>1:
                        raise PyAMLException(f"RF transmitter {t.get_name()}, multiple cavity definition:{cav[0]}")
                  if len(cav)==0:
                        raise PyAMLException(f"RF transmitter {t.get_name()}, No cavity found")
                  cavsPerTrans.append(cav[0])
                  harmonics.append(t._cfg.harmonic)
                voltage = RWRFVoltageScalar(cavsPerTrans)
                phase = RWRFPhaseScalar(cavsPerTrans)
                nt = t.attach(self,voltage,phase)
                self.add_rf_transnmitter(nt)
                cavs.extend(cavsPerTrans)
                attachedTrans.append(nt)

              frequency = RWRFFrequencyScalar(cavs,harmonics)
              voltage = RWTotalVoltage(attachedTrans)
              ne = e.attach(self,frequency,voltage)
              self.add_rf_plant(ne)             
            else:
              # No transmitter defined switch to AT methods
              frequency = RWRFATFrequencyScalar(self.ring)
              voltage = RWRFATotalVoltageScalar(self.ring)
              ne = e.attach(self,frequency,voltage)
              self.add_rf_plant(ne)

          elif isinstance(e, BetatronTuneMonitor):
             betatron_tune = RBetatronTuneArray(self.ring)
             e = e.attach(self,betatron_tune)
             self.add_betatron_tune_monitor(e)
             
    
    def get_at_elems(self,element:Element) -> list[at.Element]:
       identifier = self._linker.get_element_identifier(element)
       element_list = self._linker.get_at_elements(identifier)
       if not element_list:
          raise PyAMLException(f"{identifier} not found in lattice:{self._cfg.lattice}")
       return element_list

    def __repr__(self):
       return repr(self._cfg).replace("ConfigModel",self.__class__.__name__)