from abc import ABCMeta, abstractmethod
from ..common.element_holder import ElementHolder
from ..common.abstract import RWMapper
from ..lattice.element import Element
from ..control.abstract_impl import RWHardwareScalar,RWHardwareArray,RWStrengthScalar,RWStrengthArray
from ..bpm.bpm import BPM
from ..control.abstract_impl import RWBpmTiltScalar,RWBpmOffsetArray, RBpmArray
from ..control.abstract_impl import RWRFFrequencyScalar,RWRFVoltageScalar,RWRFPhaseScalar
from ..control.abstract_impl import CSScalarAggregator,CSStrengthScalarAggregator
from ..common.abstract_aggregator import ScalarAggregator
from ..magnet.magnet import Magnet
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..rf.rf_plant import RFPlant,RWTotalVoltage
from ..rf.rf_transmitter import RFTransmitter
from ..configuration.factory import Factory

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
    
    @abstractmethod
    def scalar_aggregator(self) -> str | None:
        """Returns the module name used for handling aggregator of DeviceAccess"""
        return None

    @abstractmethod
    def vector_aggregator(self) -> str | None:
        """Returns the module name used for handling aggregator of DeviceVectorAccess"""
        return None

    def create_scalar_aggregator(self) -> ScalarAggregator:
        mod = self.scalar_aggregator()
        agg = Factory.build_object({"type":mod}) if mod is not None else None
        return CSScalarAggregator(agg)
    
    def create_magnet_strength_aggregator(self,magnets:list[Magnet]) -> ScalarAggregator:
        agg = CSStrengthScalarAggregator(self.create_scalar_aggregator())
        for m in magnets:
            agg.add_magnet(m)
        return agg

    def create_magnet_harddware_aggregator(self,magnets:list[Magnet]) -> ScalarAggregator:
        # When working in hardware space, 1 single power supply device per multipolar strength is required
        agg = self.create_scalar_aggregator()
        for m in magnets:
            if not m.model.has_hardware():
               return None
            psIndex = m.hardware.index() if isinstance(m.hardware,RWMapper) else 0
            agg.add_devices(m.model.get_devices()[psIndex])
        return agg
    
    def create_bpm_aggregators(self,bpms:list[BPM]) -> list[ScalarAggregator]:
        agg = self.create_scalar_aggregator()
        aggh = self.create_scalar_aggregator()
        aggv = self.create_scalar_aggregator()
        for b in bpms:
            devs = b.model.get_pos_devices()
            agg.add_devices(devs)
            aggh.add_devices(devs[0])
            aggv.add_devices(devs[1])
        return [agg,aggh,aggv]


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
