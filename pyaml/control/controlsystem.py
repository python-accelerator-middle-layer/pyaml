from abc import ABCMeta, abstractmethod

from pydantic import BaseModel

from ..bpm.bpm import BPM
from ..common.abstract import RWMapper
from ..common.abstract_aggregator import ScalarAggregator
from ..common.exception import PyAMLException
from ..common.holders.element_holder import ElementHolder
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

    def fill_magnet(self, magnet: Magnet) -> None:
        device = self.get_device_access(magnet.model.get_device_names()[0])
        current = RWHardwareScalar(magnet.model, device) if magnet.model.has_hardware() else None
        strength = RWStrengthScalar(magnet.model, device) if magnet.model.has_physics() else None
        self.magnet.add(magnet.attach(self, strength, current))

    def fill_combined_function_magnet(self, magnet: CombinedFunctionMagnet) -> None:
        devices = self.get_devices_access(magnet.model.get_device_names())
        currents = RWHardwareArray(magnet.model, devices)
        strengths = RWStrengthArray(magnet.model, devices)
        attached_magnets = magnet.attach(self, strengths, currents)
        self.combined_function_magnet.add(attached_magnets[0])
        for virtual_magnet in attached_magnets[1:]:
            self.magnet.add(virtual_magnet)

    def fill_serialized_magnets(self, magnets: SerializedMagnets) -> None:
        devices = self.get_devices_access(magnets.model.get_device_names())
        currents = []
        strengths = []
        for index in range(magnets.get_nb_magnets()):
            currents.append(
                RWHardwareScalar(magnets.model.get_sub_model(index), devices[index]) if magnets.model.has_hardware() else None
            )
            strengths.append(
                RWStrengthScalar(magnets.model.get_sub_model(index), devices[index]) if magnets.model.has_physics() else None
            )
        attached_magnets = magnets.attach(self, strengths, currents)
        self.serialized_magnet.add(attached_magnets[0])
        for magnet in attached_magnets[1:]:
            self.magnet.add(magnet)

    def fill_bpm(self, bpm: BPM) -> None:
        position_devices = self.get_devices_access(bpm.get_pos_devices())
        tilt_devices = self.get_devices_access([bpm.get_tilt_device()])
        offset_devices = self.get_devices_access(bpm.get_offset_devices())
        positions = RBpmArray(position_devices[0], position_devices[1])
        tilt = RWBpmTiltScalar(tilt_devices[0])
        offsets = RWBpmOffsetArray(offset_devices[0], offset_devices[1])
        self.bpm.add(bpm.attach(self, positions, offsets, tilt))

    def fill_rf_plant(self, rf_plant: RFPlant) -> None:
        attached_transmitters: list[RFTransmitter] = []
        if rf_plant.transmitters:
            for transmitter in rf_plant.transmitters:
                voltage_device = self.get_device_access(transmitter.voltage_name)
                phase_device = self.get_device_access(transmitter.phase_name)
                voltage = RWRFVoltageScalar(transmitter, voltage_device)
                phase = RWRFPhaseScalar(transmitter, phase_device)
                attached_transmitter = transmitter.attach(self, voltage, phase)
                self.rf.transmitter.add(attached_transmitter)
                attached_transmitters.append(attached_transmitter)
        frequency_device = self.get_device_access(rf_plant.masterclock)
        frequency = RWRFFrequencyScalar(rf_plant, frequency_device)
        voltage = RWTotalVoltage(attached_transmitters) if rf_plant.transmitters else None
        self.rf.add(rf_plant.attach(self, frequency, voltage))

    def fill_betatron_tune_monitor(self, monitor: BetatronTuneMonitor) -> None:
        devices = self.get_devices_access([monitor.tune_h, monitor.tune_v])
        self.add_betatron_tune_monitor(monitor.attach(self, RBetatronTuneArray(monitor, devices)))

    def fill_tool(self, tool: TuningTool | MeasurementTool) -> None:
        self.add_tool(tool.attach(self))

    def fill_unbound_element(self, element: UnboundElement) -> None:
        if self.name() not in element._control_modes:
            return
        attached_element = element.instantiate(self)
        if isinstance(attached_element, ABetatronTuneMonitor):
            self.add_betatron_tune_monitor(attached_element)
        else:
            self.add_element(attached_element)


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
