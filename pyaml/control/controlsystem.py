import re
from abc import ABCMeta, abstractmethod
from typing import Tuple

from ..bpm.bpm import BPM
from ..bpm.bpm_model import BPMModel
from ..common.abstract import RWMapper
from ..common.abstract_aggregator import ScalarAggregator
from ..common.element import Element
from ..common.element_holder import ElementHolder
from ..common.exception import PyAMLException
from ..configuration.catalog import Catalog
from ..configuration.factory import Factory
from ..control.abstract_impl import (
    CSBPMArrayMapper,
    CSScalarAggregator,
    CSStrengthScalarAggregator,
    RBetatronTuneArray,
    RBpmArray,
    RChromaticityArray,
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
from ..diagnostics.chromaticity_monitor import ChomaticityMonitor
from ..diagnostics.tune_monitor import BetatronTuneMonitor
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..magnet.magnet import Magnet
from ..magnet.serialized_magnet import SerializedMagnets
from ..rf.rf_plant import RFPlant, RWTotalVoltage
from ..rf.rf_transmitter import RFTransmitter
from ..tuning_tools.dispersion import Dispersion
from ..tuning_tools.orbit import Orbit
from ..tuning_tools.orbit_response_matrix import OrbitResponseMatrix
from ..tuning_tools.tune import Tune
from .catalog_view import CatalogView
from .deviceaccess import DeviceAccess


class ControlSystem(ElementHolder, metaclass=ABCMeta):
    """
    Abstract class providing access to a control system float variable
    """

    def __init__(self):
        ElementHolder.__init__(self)
        self._catalog: CatalogView | None = None

    def set_catalog_view(self, catalog: CatalogView | None):
        self._catalog = catalog

    @abstractmethod
    def attach(self, dev: list[DeviceAccess]) -> list[DeviceAccess]:
        """Return new instances of DeviceAccess objects
        coming from configuration attached to this CS"""
        pass

    @abstractmethod
    def attach_array(self, dev: list[DeviceAccess]) -> list[DeviceAccess]:
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

    @abstractmethod
    def get_catalog(self) -> str | Catalog | None:
        """Returns the name of the catalog dedicated to this control system"""
        return None

    def get_catalog_name(self) -> str | None:
        """Returns the name of the catalog dedicated to this control system"""
        catalog = self.get_catalog()
        if catalog is not None:
            if isinstance(catalog, str):
                return catalog
            elif isinstance(catalog, Catalog):
                return catalog.get_name()
        return None

    def attach_indexed(self, dev: DeviceAccess, idx: int | None) -> DeviceAccess:
        if idx is not None:
            return self.attach_array([dev])[0]
        else:
            return self.attach([dev])[0]

    def create_scalar_aggregator(self) -> ScalarAggregator:
        mod = self.scalar_aggregator()
        agg = Factory.build_object({"type": mod}) if mod is not None else None
        return CSScalarAggregator(agg)

    def create_magnet_strength_aggregator(self, magnets: list[Magnet]) -> ScalarAggregator:
        agg = CSStrengthScalarAggregator(self.create_scalar_aggregator())
        for m in magnets:
            devs = self.attach(m.model.get_devices())
            agg.add_magnet(m, devs)
        return agg

    def create_magnet_hardware_aggregator(self, magnets: list[Magnet]) -> ScalarAggregator:
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
        # return [None,None,None]

        if any([not b.model.is_pos_indexed() for b in bpms]):
            # Aggregator for single BPM (all values are scalar)
            agg = self.create_scalar_aggregator()
            aggh = self.create_scalar_aggregator()
            aggv = self.create_scalar_aggregator()
            for b in bpms:
                model = b.model
                hDev = self._catalog.get_one(model.get_x_pos_device()) if model.get_x_pos_device() is not None else None
                vDev = self._catalog.get_one(model.get_y_pos_device()) if model.get_y_pos_device() is not None else None
                devs = self.attach([hDev.get_target(), vDev.get_target()])
                hDev.set_target(devs[0])
                vDev.set_target(devs[1])
                agg.add_devices(devs)
                aggh.add_devices(hDev)
                aggv.add_devices(vDev)
            return [agg, aggh, aggv]

        elif any([b.model.is_pos_indexed() for b in bpms]):
            # Aggregator for indexed BPMs
            allH = []
            hIdx = []
            allV = []
            vIdx = []
            allHV = []
            for b in bpms:
                devH = self._catalog.get_one(b.model.get_x_pos_device())
                devV = self._catalog.get_one(b.model.get_y_pos_device())
                devs = self.attach_array([devH.get_target(), devV.get_target()])
                devH.set_target(devs[0])
                devV.set_target(devs[1])
                if devH not in allH:
                    allH.append(devH)
                if devH not in allHV:
                    allHV.append(devH)
                if devV not in allV:
                    allV.append(devV)
                if devV not in allHV:
                    allHV.append(devV)
                hIdx.append(b.model.x_pos_index())
                vIdx.append(b.model.y_pos_index())

            if len(allH) > 1 or len(allV) > 1:
                # Does not support aggregator for individual BPM that
                # returns an array of [x,y]
                print("Warning, Individual BPM that returns [x,y]" + " are not read in parralell")
                # Default to serialized readding
                return [None, None, None]

            if devH == devV:
                # [x0,y0,x1,y0,....]
                idx = []
                for b in bpms:
                    idx.append(b.model.x_pos_index())
                    idx.append(b.model.y_pos_index())
                hvIdx = [idx]
            else:
                hvIdx = [hIdx, vIdx]

            agg = CSBPMArrayMapper(allHV, hvIdx)
            aggh = CSBPMArrayMapper(allH, [hIdx])
            aggv = CSBPMArrayMapper(allV, [vIdx])
            return [agg, aggh, aggv]
        else:
            raise PyAMLException("Indexed BPM and scalar values cannot be mixed in the same array")

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
                current = RWHardwareScalar(e.model, dev) if e.model.has_hardware() else None
                strength = RWStrengthScalar(e.model, dev) if e.model.has_physics() else None
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

            elif isinstance(e, SerializedMagnets):
                devs = self.attach(e.model.get_devices())
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
                model = e.model
                hDev = self._catalog.get_one(model.get_x_pos_device()) if model.get_x_pos_device() is not None else None
                vDev = self._catalog.get_one(model.get_y_pos_device()) if model.get_y_pos_device() is not None else None
                tiltDev = (
                    self._catalog.get_one(model.get_tilt_device()) if model.get_tilt_device() is not None else None
                )
                hOffsetDev = (
                    self._catalog.get_one(model.get_x_offset_device())
                    if model.get_x_offset_device() is not None
                    else None
                )
                vOffsetDev = (
                    self._catalog.get_one(model.get_y_offset_device())
                    if model.get_y_offset_device() is not None
                    else None
                )
                ahDev = self.attach_indexed(hDev.get_target() if hDev is not None else None, model.x_pos_index())
                avDev = self.attach_indexed(vDev.get_target() if vDev is not None else None, model.y_pos_index())
                atiltDev = self.attach_indexed(
                    tiltDev.get_target() if tiltDev is not None else None,
                    model.tilt_index(),
                )
                ahOffsetDev = self.attach_indexed(
                    hOffsetDev.get_target() if hOffsetDev is not None else None,
                    model.x_offset_index(),
                )
                avOffsetDev = self.attach_indexed(
                    vOffsetDev.get_target() if vOffsetDev is not None else None,
                    model.y_offset_index(),
                )
                if ahDev is not None:
                    hDev.set_target(ahDev)
                if avDev is not None:
                    vDev.set_target(avDev)
                if atiltDev is not None:
                    tiltDev.set_target(atiltDev)
                if ahOffsetDev is not None:
                    hOffsetDev.set_target(ahOffsetDev)
                if avOffsetDev is not None:
                    vOffsetDev.set_target(avOffsetDev)
                positions = RBpmArray(model, hDev, vDev)
                tilt = RWBpmTiltScalar(model, tiltDev)
                offsets = RWBpmOffsetArray(model, hOffsetDev, vOffsetDev)
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

            elif isinstance(e, ChomaticityMonitor):
                chromaticity = RChromaticityArray(e)
                e = e.attach(self, chromaticity)
                self.add_chromaticity_monitor(e)

            elif isinstance(e, Tune):
                self.add_tune_tuning(e.attach(self))

            elif isinstance(e, Orbit):
                self.add_orbit_tuning(e.attach(self))

            elif isinstance(e, OrbitResponseMatrix):
                self.add_orm_tuning(e.attach(self))

            elif isinstance(e, Dispersion):
                self.add_dispersion_tuning(e.attach(self))
