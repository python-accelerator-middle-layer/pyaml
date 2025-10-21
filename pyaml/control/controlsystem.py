from abc import ABCMeta, abstractmethod
from ..lattice.element_holder import ElementHolder
from ..lattice.element import Element
from ..control.abstract_impl import RWHardwareScalar,RWHardwareArray,RWStrengthScalar,RWStrengthArray
from ..bpm.bpm import BPM
from ..control.abstract_impl import RWBpmTiltScalar,RWBpmOffsetArray, RBpmArray
from ..control.abstract_impl import RWRFFrequencyScalar,RWRFVoltageScalar,RWRFPhaseScalar
from ..magnet.magnet import Magnet
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..rf.rf_plant import RFPlant,RWTotalVoltage
from ..rf.rf_transmitter import RFTransmitter

class ControlSystem(ElementHolder,metaclass=ABCMeta):
    """
    Abstract class providing access to a control system float variable
    """

    def __init__(self):
        ElementHolder.__init__(self)

    @abstractmethod
    def init_cs(self):
        """Initialize control system"""
        pass

    @abstractmethod
    def name(self) -> str:
        """Return control system name (i.e. live)"""
        pass

    def set_energy(self,E:float):
        """
        Sets the energy on magnets belonging to this control system
        
        Parameters
        ----------
        E : float
            Energy in eV
        """
        for m in self.get_all_magnets().items():
            m[1].set_energy(E)
    
    def fill_device(self,elements:list[Element]):
        """
        Fill device of this control system with Element coming from the configuration file
        
        Parameters
        ----------
        elements : list[Element]
            List of elements coming from the configuration file to attach to this control system
        """           
        for e in elements:
          if isinstance(e,Magnet):
            current = RWHardwareScalar(e.model) if e.model.has_hardware() else None
            strength = RWStrengthScalar(e.model) if e.model.has_physics() else None
            # Create a unique ref for this control system
            m = e.attach(strength, current)
            self.add_magnet(m.get_name(),m)

          elif isinstance(e,CombinedFunctionMagnet):
            self.add_magnet(e.get_name(),e)
            currents = RWHardwareArray(e.model) if e.model.has_hardware() else None
            strengths = RWStrengthArray(e.model) if e.model.has_physics() else None
            # Create unique refs of each function for this control system
            ms = e.attach(strengths,currents)
            for m in ms:
              self.add_magnet(m.get_name(),m)
          elif isinstance(e,BPM):
            tilt = RWBpmTiltScalar(e.model)
            offsets = RWBpmOffsetArray(e.model)
            positions = RBpmArray(e.model)
            e = e.attach(positions, offsets, tilt)
            self.add_bpm(e.get_name(),e)


          elif isinstance(e,RFPlant):
             self.add_rf_plant(e.get_name(),e)
             attachedTrans: list[RFTransmitter] = []
             for t in e._cfg.transmitters:
                voltage = RWRFVoltageScalar(t)
                phase = RWRFPhaseScalar(t)
                nt = t.attach(voltage,phase)
                self.add_rf_transnmitter(nt.get_name(),nt)
                attachedTrans.append(nt)

             frequency = RWRFFrequencyScalar(e)
             voltage = RWTotalVoltage(attachedTrans)
             ne = e.attach(frequency,voltage)
             self.add_rf_plant(ne.get_name(),ne)
