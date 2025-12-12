from abc import ABCMeta, abstractmethod

from ..bpm.bpm import BPM
from ..common.abstract import RWMapper
from ..common.abstract_aggregator import ScalarAggregator
from ..common.element import Element
from ..common.element_holder import ElementHolder
from ..configuration.factory import Factory
from ..control.abstract_impl import (
    CSScalarAggregator,
    CSStrengthScalarAggregator,
    RBetatronTuneArray,
    RBpmArray,
    RWBpmOffsetArray,
    RWBpmTiltScalar,
    RWHardwareArray,
    RWHardwareScalar,
    RWRFFrequencyScalar,
    RWRFPhaseScalar,
    RWRFVoltageScalar,
    RWStrengthArray,
    RWStrengthScalar,
)
from ..diagnostics.tune_monitor import BetatronTuneMonitor
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..magnet.magnet import Magnet
from ..rf.rf_plant import RFPlant, RWTotalVoltage
from ..rf.rf_transmitter import RFTransmitter
from ..tuning_tools.orbit import Orbit
from ..tuning_tools.tune import Tune
from .deviceaccess import DeviceAccess


class ControlSystem(ElementHolder, metaclass=ABCMeta):
    """
    Abstract class providing access to a control system float variable
    """

    def __init__(self):
        ElementHolder.__init__(self)

    @abstractmethod
    def attach(self, dev: list[DeviceAccess]) -> list[DeviceAccess]:
        """Return new instances of DeviceAccess objects
        coming from configuration attached to this CS"""
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
        agg = Factory.build_object({"type": mod}) if mod is not None else None
        return CSScalarAggregator(agg)

    def create_magnet_strength_aggregator(
        self, magnets: list[Magnet]
    ) -> ScalarAggregator:
        agg = CSStrengthScalarAggregator(self.create_scalar_aggregator())
        for m in magnets:
            devs = self.attach(m.model.get_devices())
            agg.add_magnet(m, devs)
        return agg

    def create_magnet_harddware_aggregator(
        self, magnets: list[Magnet]
    ) -> ScalarAggregator:
        """When working in hardware space, 1 single power
        supply device per multipolar strength is required
        """
        agg = self.create_scalar_aggregator()
        for m in magnets:
            if not m.model.has_hardware():
                return None
            psIndex = m.hardware.index() if isinstance(m.hardware, RWMapper) else 0
            agg.add_devices(self.attach([m.model.get_devices()[psIndex]])[0])
        return agg

    def create_bpm_aggregators(self, bpms: list[BPM]) -> list[ScalarAggregator]:
        agg = self.create_scalar_aggregator()
        aggh = self.create_scalar_aggregator()
        aggv = self.create_scalar_aggregator()
        for b in bpms:
            devs = self.attach(b.model.get_pos_devices())
            agg.add_devices(devs)
            aggh.add_devices(devs[0])
            aggv.add_devices(devs[1])
        return [agg, aggh, aggv]

    def set_energy(self, E: float):
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

    def fill_device(self, elements: list[Element]):
        """
        Fill device of this control system with Element
        coming from the configuration file

        Parameters
        ----------
        elements : list[Element]
            List of elements coming from the configuration
            file to attach to this control system
        """
        for e in elements:
            if isinstance(e, Magnet):
                dev = self.attach(e.model.get_devices())[0]
                current = (
                    RWHardwareScalar(e.model, dev) if e.model.has_hardware() else None
                )
                strength = (
                    RWStrengthScalar(e.model, dev) if e.model.has_physics() else None
                )
                # Create a unique ref for this control system
                m = e.attach(self, strength, current)
                self.add_magnet(m)

            elif isinstance(e, CombinedFunctionMagnet):
                devs = self.attach(e.model.get_devices())
                currents = RWHardwareArray(e.model, devs)
                strengths = RWStrengthArray(e.model, devs)
                # Create unique refs the cfm and
                # each of its function for this control system
                ms = e.attach(self, strengths, currents)
                self.add_cfm_magnet(ms[0])
                for m in ms[1:]:
                    self.add_magnet(m)

            elif isinstance(e, BPM):
                tiltDev = self.attach([e.model.get_tilt_device()])[0]
                offsetsDevs = self.attach(e.model.get_offset_devices())
                posDevs = self.attach(e.model.get_pos_devices())
                tilt = RWBpmTiltScalar(e.model, tiltDev)
                offsets = RWBpmOffsetArray(e.model, offsetsDevs)
                positions = RBpmArray(e.model, posDevs)
                e = e.attach(self, positions, offsets, tilt)
                self.add_bpm(e)

            elif isinstance(e, RFPlant):
                attachedTrans: list[RFTransmitter] = []
                if e._cfg.transmitters:
                    for t in e._cfg.transmitters:
                        vDev = self.attach([t._cfg.voltage])[0]
                        pDev = self.attach([t._cfg.phase])[0]
                        voltage = RWRFVoltageScalar(t, vDev)
                        phase = RWRFPhaseScalar(t, pDev)
                        nt = t.attach(self, voltage, phase)
                        self.add_rf_transnmitter(nt)
                        attachedTrans.append(nt)

                fDev = self.attach([e._cfg.masterclock])[0]
                frequency = RWRFFrequencyScalar(e, fDev)
                voltage = RWTotalVoltage(attachedTrans) if e._cfg.transmitters else None
                ne = e.attach(self, frequency, voltage)
                self.add_rf_plant(ne)

            elif isinstance(e, BetatronTuneMonitor):
                tuneDevs = self.attach([e._cfg.tune_h, e._cfg.tune_v])
                betatron_tune = RBetatronTuneArray(e, tuneDevs)
                e = e.attach(self, betatron_tune)
                self.add_betatron_tune_monitor(e)

            elif isinstance(e, Tune):
                self.add_tune_tuning(e.attach(self))

            elif isinstance(e, Orbit):
                self.add_orbit_tuning(e.attach(self))
