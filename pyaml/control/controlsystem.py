from abc import ABCMeta, abstractmethod
from ..common.element_holder import ElementHolder
from ..common.abstract import RWMapper
from ..common.element import Element
from ..control.abstract_impl import RWHardwareScalar,RWHardwareArray,RWStrengthScalar,RWStrengthArray
from ..bpm.bpm import BPM
from ..diagnostics.tune_monitor import BetatronTuneMonitor
from ..control.abstract_impl import RWBpmTiltScalar,RWBpmOffsetArray, RBpmArray
from ..control.abstract_impl import RWRFFrequencyScalar,RWRFVoltageScalar,RWRFPhaseScalar
from ..control.abstract_impl import CSScalarAggregator,CSStrengthScalarAggregator
from ..common.abstract_aggregator import ScalarAggregator
from ..control.abstract_impl import RBetatronTuneArray
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
        # Needed by energy dependant element (i.e. magnet coil current calculation)
        for m in self.get_all_elements():
            m.set_energy(E)
    
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
            m = e.attach(self,strength, current)
            self.add_magnet(m)

          elif isinstance(e,CombinedFunctionMagnet):
            currents = RWHardwareArray(e.model) if e.model.has_hardware() else None
            strengths = RWStrengthArray(e.model) if e.model.has_physics() else None
            # Create unique refs the cfm and each of its function for this control system
            ms = e.attach(self,strengths,currents)
            self.add_cfm_magnet(ms[0])
            for m in ms[1:]:
              self.add_magnet(m)

          elif isinstance(e,BPM):
            tilt = RWBpmTiltScalar(e.model)
            offsets = RWBpmOffsetArray(e.model)
            positions = RBpmArray(e.model)
            e = e.attach(self,positions, offsets, tilt)
            self.add_bpm(e)


          elif isinstance(e,RFPlant):
             attachedTrans: list[RFTransmitter] = []
             if e._cfg.transmitters:
                for t in e._cfg.transmitters:
                    voltage = RWRFVoltageScalar(t)
                    phase = RWRFPhaseScalar(t)
                    nt = t.attach(self,voltage,phase)
                    self.add_rf_transnmitter(nt)
                    attachedTrans.append(nt)

             frequency = RWRFFrequencyScalar(e)
             voltage = RWTotalVoltage(attachedTrans) if e._cfg.transmitters else None
             ne = e.attach(self,frequency,voltage)
             self.add_rf_plant(ne)

          elif isinstance(e,BetatronTuneMonitor):
              betatron_tune = RBetatronTuneArray(e)
              e = e.attach(self,betatron_tune)
              self.add_betatron_tune_monitor(e)
