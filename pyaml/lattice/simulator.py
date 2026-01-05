from pathlib import Path

import at
from pydantic import BaseModel, ConfigDict

from ..bpm.bpm import BPM
from ..common.abstract_aggregator import ScalarAggregator
from ..common.element import Element
from ..common.element_holder import ElementHolder
from ..common.exception import PyAMLException
from ..configuration import get_root_folder
from ..diagnostics.tune_monitor import BetatronTuneMonitor
from ..lattice.abstract_impl import (
    BPMHScalarAggregator,
    BPMScalarAggregator,
    BPMVScalarAggregator,
    RBetatronTuneArray,
    RBpmArray,
    RWBpmOffsetArray,
    RWBpmTiltScalar,
    RWHardwareArray,
    RWHardwareScalar,
    RWSerializedHardware,
    RWSerializedStrength,
    RWHardwareIntegratedScalar,
    RWStrengthIntegratedScalar,
    RWRFATFrequencyScalar,
    RWRFATotalVoltageScalar,
    RWRFFrequencyScalar,
    RWRFPhaseScalar,
    RWRFVoltageScalar,
    RWStrengthArray,
    RWStrengthScalar,
)
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..magnet.serialized_magnet import SerializedMagnetsModel
from ..magnet.magnet import Magnet
from ..rf.rf_plant import RFPlant, RWTotalVoltage
from ..rf.rf_transmitter import RFTransmitter
from ..tuning_tools.orbit import Orbit
from ..tuning_tools.tune import Tune
from .attribute_linker import (
    ConfigModel as PyAtAttrLinkerConfigModel,
)
from .attribute_linker import (
    PyAtAttributeElementsLinker,
)
from .lattice_elements_linker import LatticeElementsLinker

# Define the main class name for this module
PYAMLCLASS = "Simulator"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

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
        path: Path = get_root_folder() / cfg.lattice

        if self._cfg.mat_key is None:
            self.ring = at.load_lattice(path)
        else:
            self.ring = at.load_lattice(path, mat_key=f"{self._cfg.mat_key}")

        self._linker = cfg.linker
        if self._linker:
            self._linker.set_lattice(self.ring)
        else:
            self._elements_indexing = {}
            for e in self.ring:
                if e.FamName in self._elements_indexing:
                    self._elements_indexing[e.FamName].append(e)
                else:
                    self._elements_indexing[e.FamName] = [e]

    def name(self) -> str:
        return self._cfg.name

    def get_lattice(self) -> at.Lattice:
        return self.ring

    def set_energy(self, E: float):
        self.ring.energy = E
        # Needed by energy dependant element (i.e. magnet coil current calculation)
        for m in self.get_all_elements():
            m.set_energy(E)

    def create_magnet_strength_aggregator(
        self, magnets: list[Magnet]
    ) -> ScalarAggregator:
        # No magnet aggregator for simulator
        return None

    def create_magnet_harddware_aggregator(
        self, magnets: list[Magnet]
    ) -> ScalarAggregator:
        # No magnet aggregator for simulator
        return None

    def create_bpm_aggregators(self, bpms: list[BPM]) -> list[ScalarAggregator]:
        agg = BPMScalarAggregator(self.get_lattice())
        aggh = BPMHScalarAggregator(self.get_lattice())
        aggv = BPMVScalarAggregator(self.get_lattice())
        for b in bpms:
            e = self.get_at_elems(b)[0]
            agg.add_elem(e)
            aggh.add_elem(e)
            aggv.add_elem(e)
        return [agg, aggh, aggv]

    def fill_device(self, elements: list[Element]):
        for e in elements:
            # Need conversion to physics unit to work with simulator
            if isinstance(e, Magnet):
                current = (
                    RWHardwareScalar(self.get_at_elems(e), e.polynom, e.model)
                    if e.model.has_physics()
                    else None
                )
                strength = (
                    RWStrengthScalar(self.get_at_elems(e), e.polynom, e.model)
                    if e.model.has_physics()
                    else None
                )
                # Create a unique ref for this simulator
                m = e.attach(self, strength, current)
                self.add_magnet(m)

            elif isinstance(e, CombinedFunctionMagnet):
                currents = (
                    RWHardwareArray(self.get_at_elems(e), e.polynoms, e.model)
                    if e.model.has_physics()
                    else None
                )
                strengths = (
                    RWStrengthArray(self.get_at_elems(e), e.polynoms, e.model)
                    if e.model.has_physics()
                    else None
                )
                # Create unique refs of each function for this simulator
                ms = e.attach(self, strengths, currents)
                self.add_cfm_magnet(ms[0])
                for m in ms[1:]:
                    self.add_magnet(m)

            elif isinstance(e, SerializedMagnetsModel):
                currents = []
                strengths = []
                # Create unique refs the series and each of its function for this control system
                # Link hardware to strengths and bind strength together
                for index, magnet in enumerate(e.get_magnets()):
                    current = RWHardwareIntegratedScalar(self.get_at_elems(magnet), e.polynom, e.model.get_sub_model(
                        index)) if e.model.has_hardware() else None
                    strength = RWStrengthIntegratedScalar(self.get_at_elems(magnet), e.polynom, e.model.get_sub_model(
                        index)) if e.model.has_physics() else None
                    currents.append(current)
                    strengths.append(strength)
                linked_currents = []
                linked_strengths = []
                for i in range(e.get_nb_magnets()):
                    current = RWSerializedHardware(currents, i) if e.model.has_hardware() else None
                    strength = RWSerializedStrength(strengths[i], currents, i) if e.model.has_physics() else None
                    linked_currents.append(current)
                    linked_strengths.append(strength)
                ms = e.attach(self, linked_strengths, linked_currents)
                for m in ms:
                    self.add_magnet(m)

            elif isinstance(e, BPM):
                # This assumes unique BPM names in the pyAT lattice
                tilt = RWBpmTiltScalar(self.get_at_elems(e)[0])
                offsets = RWBpmOffsetArray(self.get_at_elems(e)[0])
                positions = RBpmArray(self.get_at_elems(e)[0], self.ring)
                e = e.attach(self, positions, offsets, tilt)
                self.add_bpm(e)

            elif isinstance(e, RFPlant):
                if e._cfg.transmitters:
                    cavs: list[at.Element] = []
                    harmonics: list[float] = []
                    attachedTrans: list[RFTransmitter] = []
                    for t in e._cfg.transmitters:
                        cavsPerTrans: list[at.Element] = []
                        for c in t._cfg.cavities:
                            # Expect unique name for cavities
                            cav = self.get_at_elems(Element(c))
                            if len(cav) > 1:
                                raise PyAMLException(
                                    f"RF transmitter {t.get_name()},"
                                    "multiple cavity definition:{cav[0]}"
                                )
                            if len(cav) == 0:
                                raise PyAMLException(
                                    f"RF transmitter {t.get_name()}, No cavity found"
                                )
                            cavsPerTrans.append(cav[0])
                            harmonics.append(t._cfg.harmonic)
                        voltage = RWRFVoltageScalar(cavsPerTrans)
                        phase = RWRFPhaseScalar(cavsPerTrans)
                        nt = t.attach(self, voltage, phase)
                        self.add_rf_transnmitter(nt)
                        cavs.extend(cavsPerTrans)
                        attachedTrans.append(nt)

                    frequency = RWRFFrequencyScalar(cavs, harmonics)
                    voltage = RWTotalVoltage(attachedTrans)
                    ne = e.attach(self, frequency, voltage)
                    self.add_rf_plant(ne)
                else:
                    # No transmitter defined switch to AT methods
                    frequency = RWRFATFrequencyScalar(self.ring)
                    voltage = RWRFATotalVoltageScalar(self.ring)
                    ne = e.attach(self, frequency, voltage)
                    self.add_rf_plant(ne)

            elif isinstance(e, BetatronTuneMonitor):
                betatron_tune = RBetatronTuneArray(self.ring)
                e = e.attach(self, betatron_tune)
                self.add_betatron_tune_monitor(e)

            elif isinstance(e, Tune):
                self.add_tune_tuning(e.attach(self))

            elif isinstance(e, Orbit):
                self.add_orbit_tuning(e.attach(self))

    def get_names(self, element: Element) -> list[str] | None:
        """
        Parse element lattice_name syntax. see Element.ConfigModel.lattice_name.
        """
        pattern = element.get_lattice_names()
        if pattern is None:
            return None
        if pattern.startswith("list("):
            try:
                return pattern[5:-1].rsplit(",")
            except Exception as err:
                strErr = f"{element.get_name()}: Invalid lattice_names syntax "
                strErr += f"for {pattern}, {str(err)}"
                raise PyAMLException(strErr) from err
        return None

    def get_indices(self, element: Element) -> (str | None, list[int] | None):
        """
        Parse element lattice_name syntax. see Element.ConfigModel.lattice_name.
        """

        pattern = element.get_lattice_names()
        if pattern is None:
            return (element.get_name(), None)

        # [name]@idx[,idx] syntax
        split = pattern.rfind("@")
        if split >= 0:
            try:
                name = pattern[:split]
                l = pattern[split + 1 :]
                lidx = l.rsplit(",")
                rlist = list(map(int, lidx))
                return (name if len(name) > 0 else None, rlist)
            except Exception as err:
                strErr = f"{element.get_name()}: Invalid lattice_names syntax "
                strErr += f"for {pattern}, {str(err)}"
                raise PyAMLException(strErr) from err

        # [name]#start_idx..end_idx syntax
        split = pattern.rfind("#")
        if split >= 0:
            try:
                name = pattern[:split]
                l = pattern[split + 1 :]
                lrange = l.rsplit("..")
                sl = list(map(int, lrange))
                rlist = range(sl[0], sl[1])
                return (name if len(name) > 0 else None, rlist)
            except Exception as err:
                strErr = f"{element.get_name()}: Invalid lattice_names syntax "
                strErr += f"for {pattern}, {str(err)}"
                raise PyAMLException(strErr) from err

        return (element.get_name(), None)

    def get_at_elems(self, element: Element) -> list[at.Element]:
        if self._linker:
            identifier = self._linker.get_element_identifier(element)
            element_list = self._linker.get_at_elements(identifier)
            if not element_list:
                raise PyAMLException(
                    f"{identifier} not found in lattice:{self._cfg.lattice}"
                )
            return element_list
        else:
            # By list
            nameList = self.get_names(element)

            if nameList is not None:
                names = []
                for name in nameList:
                    if name not in self._elements_indexing:
                        raise PyAMLException(
                            f"{name} not found in lattice:{self._cfg.lattice}"
                        )
                    elts = self._elements_indexing[name]
                    names.extend(elts)
                return names

            # By name or indices
            name, indices = self.get_indices(element)

            if name is None:
                # Direct indexing in the ring
                return [self.ring[idx] for idx in indices]
            else:
                if name not in self._elements_indexing:
                    raise PyAMLException(
                        f"{name} not found in lattice:{self._cfg.lattice}"
                    )
                elts = self._elements_indexing[name]
                if indices is None:
                    return elts
                else:
                    return [elts[idx] for idx in indices]

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
