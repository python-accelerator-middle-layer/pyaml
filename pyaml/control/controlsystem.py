from abc import ABCMeta, abstractmethod

from pydantic import BaseModel

from ..bpm.bpm import BPM
from ..common.abstract import RWMapper
from ..common.abstract_aggregator import ScalarAggregator
from ..common.element import Element
from ..common.element_holder import ElementHolder
from ..common.exception import PyAMLException
from ..configuration.factory import Factory
from ..configuration.unbound_element import UnboundElement
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
from ..diagnostics.atune_monitor import ABetatronTuneMonitor
from ..diagnostics.tune_monitor import BetatronTuneMonitor
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..magnet.magnet import Magnet
from ..magnet.serialized_magnet import SerializedMagnets
from ..rf.rf_plant import RFPlant, RWTotalVoltage
from ..rf.rf_transmitter import RFTransmitter
from ..tuning_tools.measurement_tool import MeasurementTool
from ..tuning_tools.tuning_tool import TuningTool
from .deviceaccess import DeviceAccess
from .deviceaccesslist import DeviceAccessList


class ControlSystem(ElementHolder, metaclass=ABCMeta):
    """
    Abstract class providing access to a control system float variable
    """

    def __init__(self):
        ElementHolder.__init__(self)

    @abstractmethod
    def name(self) -> str:
        """Return control system name (i.e. live)"""
        pass

    @abstractmethod
    def get_aggregator(self) -> DeviceAccessList | None:
        """Returns a new empty DeviceAccessList. If None is returned serialized readings/writtings are performed"""
        pass

    @abstractmethod
    def get_device_access(self, ref: str | BaseModel | None) -> DeviceAccess:
        """
        Return a device reference for this control system.
        YAML element configuration passes opaque strings. Public Python APIs may
        also pass backend ConfigModel instances. Concrete backends own all
        lookup, parsing and DeviceAccess construction.
        """
        pass

    def get_devices_access(self, refs: list[str | BaseModel | None]) -> list[DeviceAccess]:
        """
        Return a device reference for this control system.
        YAML element configuration passes opaque strings. Public Python APIs may
        also pass backend ConfigModel instances. Concrete backends own all
        lookup, parsing and DeviceAccess construction.
        """
        if not isinstance(refs, list):
            raise PyAMLException(f"get_devices() expect a list as input arguments but got {str(type(refs))}")
        return [self.get_device_access(ref) for ref in refs]

    def _create_scalar_aggregator(self) -> ScalarAggregator | None:
        agg = self.get_aggregator()
        if agg is None:
            return None
        return CSScalarAggregator(agg)

    def create_magnet_strength_aggregator(self, magnets: list[Magnet]) -> ScalarAggregator | None:
        agg = self._create_scalar_aggregator()
        if agg is None:
            return None
        magg = CSStrengthScalarAggregator(agg)
        for m in magnets:
            devs = self.get_devices_access(m.model.get_device_names())
            magg.add_magnet(m, devs)
        return magg

    def create_magnet_hardware_aggregator(self, magnets: list[Magnet]) -> ScalarAggregator | None:
        """When working in hardware space, 1 single power
        supply device per multipolar strength is required
        """
        agg = self._create_scalar_aggregator()
        if agg is None:
            return None
        for m in magnets:
            if not m.model.has_hardware():
                return None
            psIndex = m.hardware.index() if isinstance(m.hardware, RWMapper) else 0
            agg.add_devices(self.get_devices_access([m.model.get_device_names()[psIndex]])[0])
        return agg

    def create_bpm_aggregators(self, bpms: list[BPM]) -> list[ScalarAggregator | None]:
        agg = self._create_scalar_aggregator()
        aggh = self._create_scalar_aggregator()
        aggv = self._create_scalar_aggregator()
        if agg is None or aggh is None or aggv is None:
            return [None, None, None]
        for b in bpms:
            devs = self.get_devices_access(b.get_pos_devices())
            agg.add_devices(devs)
            aggh.add_devices(devs[0])
            aggv.add_devices(devs[1])
        return [agg, aggh, aggv]

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
                dev = self.get_device_access(e.model.get_device_names()[0])
                current = RWHardwareScalar(e.model, dev) if e.model.has_hardware() else None
                strength = RWStrengthScalar(e.model, dev) if e.model.has_physics() else None
                # Create a unique ref for this control system
                m = e.attach(self, strength, current)
                self.add_magnet(m)

            elif isinstance(e, CombinedFunctionMagnet):
                devs = self.get_devices_access(e.model.get_device_names())
                currents = RWHardwareArray(e.model, devs)
                strengths = RWStrengthArray(e.model, devs)
                # Create unique refs the cfm and
                # each of its function for this control system
                ms = e.attach(self, strengths, currents)
                self.add_cfm_magnet(ms[0])
                for m in ms[1:]:
                    self.add_magnet(m)

            elif isinstance(e, SerializedMagnets):
                devs = self.get_devices_access(e.model.get_device_names())
                currents = []
                strengths = []
                # Create unique refs the series and each of its function for this
                # control system
                for i in range(e.get_nb_magnets()):
                    current = RWHardwareScalar(e.model.get_sub_model(i), devs[i]) if e.model.has_hardware() else None
                    strength = RWStrengthScalar(e.model.get_sub_model(i), devs[i]) if e.model.has_physics() else None
                    currents.append(current)
                    strengths.append(strength)
                ms = e.attach(self, strengths, currents)
                self.add_serialized_magnet(ms[0])
                for m in ms[1:]:
                    self.add_magnet(m)

            elif isinstance(e, BPM):
                pos_devs = self.get_devices_access(e.get_pos_devices())
                tilt_devs = self.get_devices_access([e.get_tilt_device()])
                offset_devs = self.get_devices_access(e.get_offset_devices())
                positions = RBpmArray(pos_devs[0], pos_devs[1])
                tilt = RWBpmTiltScalar(tilt_devs[0])
                offsets = RWBpmOffsetArray(offset_devs[0], offset_devs[1])
                e = e.attach(self, positions, offsets, tilt)
                self.add_bpm(e)

            elif isinstance(e, RFPlant):
                attachedTrans: list[RFTransmitter] = []
                if e._cfg.transmitters:
                    for t in e._cfg.transmitters:
                        vDev = self.get_device_access(t._cfg.voltage)
                        pDev = self.get_device_access(t._cfg.phase)
                        voltage = RWRFVoltageScalar(t, vDev)
                        phase = RWRFPhaseScalar(t, pDev)
                        nt = t.attach(self, voltage, phase)
                        self.add_rf_transnmitter(nt)
                        attachedTrans.append(nt)

                fDev = self.get_device_access(e._cfg.masterclock)
                frequency = RWRFFrequencyScalar(e, fDev)
                voltage = RWTotalVoltage(attachedTrans) if e._cfg.transmitters else None
                ne = e.attach(self, frequency, voltage)
                self.add_rf_plant(ne)

            elif isinstance(e, BetatronTuneMonitor):
                # Built in tune monitor
                tuneDevs = self.get_devices_access([e._cfg.tune_h, e._cfg.tune_v])
                betatron_tune = RBetatronTuneArray(e, tuneDevs)
                e = e.attach(self, betatron_tune)
                self.add_betatron_tune_monitor(e)

            elif isinstance(e, TuningTool) | isinstance(e, MeasurementTool):
                self.add_tool(e.attach(self))

            elif isinstance(e, UnboundElement):
                if self.name() in e._control_modes:
                    ne = e.instantiate(self)

                    if isinstance(ne, ABetatronTuneMonitor):
                        self.add_betatron_tune_monitor(ne)
                    else:
                        # Default to standard Element
                        self.add_element(ne)


class ControlSystemAdapter(ControlSystem):
    """
    Control system adapter class
    """

    def __init__(self):
        ControlSystem.__init__(self)

    def name(self) -> str:
        pass

    def get_aggregator(self) -> DeviceAccessList | None:
        return None

    def get_device_access(self, ref: str | BaseModel | None) -> DeviceAccess | None:
        pass
