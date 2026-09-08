"""
PyAT-backed accelerator simulator interfaces.

This module loads Accelerator Toolbox lattices and binds PyAML elements to
their simulated lattice counterparts.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import at

from ..bpm.bpm import BPM
from ..common.abstract_aggregator import ScalarAggregator
from ..common.element import Element, __pyaml_repr__
from ..common.exception import PyAMLException
from ..common.holders.element_holder import ElementHolder
from ..configuration import ROOT
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
    RWRFATFrequencyScalar,
    RWRFATotalVoltageScalar,
    RWRFFrequencyScalar,
    RWRFPhaseScalar,
    RWRFVoltageScalar,
    RWSerializedHardware,
    RWSerializedStrength,
    RWStrengthArray,
    RWStrengthScalar,
    update_bpm_transform_matrix,
)
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..magnet.magnet import Magnet
from ..magnet.serialized_magnet import SerializedMagnets
from ..rf.rf_plant import RFPlant, RWTotalVoltage
from ..rf.rf_transmitter import RFTransmitter
from ..tuning_tools.measurement_tool import MeasurementTool
from ..tuning_tools.tuning_tool import TuningTool
from ..validation import DynamicValidation, register_schema
from .lattice_elements_linker import LatticeElementsLinker

if TYPE_CHECKING:
    from ..configuration.unbound_element import UnboundElement

# Define the main class name for this module
PYAMLCLASS = "Simulator"


@register_schema
class Simulator(ElementHolder, DynamicValidation):
    """
    Simulator interface backed by a PyAT lattice.

    The simulator loads a PyAT lattice from disk and attaches PyAML
    elements to their corresponding PyAT elements. Once attached, the
    resulting device objects expose read/write interfaces operating
    directly on the simulation model.

    Elements may be matched either using the default name-based lookup
    or a custom :class:`LatticeElementsLinker`.

    Parameters
    ----------
    name : str
        Name of the simulator.
    lattice : str
        Path to the PyAT lattice file, relative to the configured
        PyAML root directory.
    mat_key : str, optional
        Variable name of the lattice when loading a MATLAB ``.mat``
        lattice file.
    linker : LatticeElementsLinker, optional
        Custom linker used to associate PyAML elements with PyAT
        lattice elements. If omitted, elements are matched by name.
    description : str, optional
        Human-readable description of the simulator.

    Attributes
    ----------
    lattice
        Underlying PyAT lattice.
    mat_key
        Key used to read the lattice out of a MATLAB file.

    Methods
    -------
    name()
        Return the simulator name.
    get_lattice()
        Return the loaded Accelerator Toolbox lattice.
    get_description()
        Returns the description of the accelerator
    create_magnet_strength_aggregator(magnets)
        Return the magnet-strength aggregator for this simulator.
    create_magnet_hardware_aggregator(magnets)
        Return the magnet-hardware aggregator for this simulator.
    create_bpm_aggregators(bpms)
        Create BPM position aggregators for the loaded lattice.
    fill_device(elements)
        Attach PyAML elements to their matching PyAT lattice elements.
    get_names(element)
        Parse element lattice_name syntax. see Element.ConfigModel.lattice_name.
    get_indices(element)
        Parse element lattice_name syntax. see Element.ConfigModel.lattice_name.
    get_at_elems(element)
        Resolve a PyAML element to matching PyAT lattice elements.
    """

    def __init__(
        self,
        name: str,
        lattice: str,
        mat_key: str | None = None,
        linker: LatticeElementsLinker | None = None,
        description: str | None = None,
    ):
        """
        Create a simulator from a PyAT lattice.
        """

        super().__init__()
        self._name = name
        self._lattice = lattice
        self._mat_key = mat_key
        self.description = description

        path: Path = ROOT.get() / self._lattice

        if self._mat_key is None:
            self.ring = at.load_lattice(path)
        else:
            self.ring = at.load_lattice(path, mat_key=f"{self._mat_key}")

        self._linker = linker
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
        """Return the simulator name."""
        return self._name

    @property
    def lattice(self) -> str:
        """Return the configured lattice file path."""
        return self._lattice

    def get_lattice(self) -> at.Lattice:
        """Return the loaded Accelerator Toolbox lattice."""
        return self.ring

    @property
    def mat_key(self) -> str | None:
        """Return the MATLAB variable name used to load the lattice."""
        return self._mat_key

    def get_description(self) -> str | None:
        """
        Returns the description of the accelerator
        """
        return self.description

    def create_magnet_strength_aggregator(self, magnets: list[Magnet]) -> ScalarAggregator:
        # No magnet aggregator for simulator
        """
        Return the magnet-strength aggregator for this simulator.

        Parameters
        ----------
        magnets : list[Magnet]
            Magnets for which aggregation was requested.

        Returns
        -------
        ScalarAggregator
            ``None`` because simulated magnet values are accessed directly.
        """
        return None

    def create_magnet_hardware_aggregator(self, magnets: list[Magnet]) -> ScalarAggregator:
        # No magnet aggregator for simulator
        """
        Return the magnet-hardware aggregator for this simulator.

        Parameters
        ----------
        magnets : list[Magnet]
            Magnets for which aggregation was requested.

        Returns
        -------
        ScalarAggregator
            ``None`` because simulated hardware values are accessed directly.
        """
        return None

    def create_bpm_aggregators(self, bpms: list[BPM]) -> list[ScalarAggregator]:
        """
        Create BPM position aggregators for the loaded lattice.

        Parameters
        ----------
        bpms : list[BPM]
            BPM elements whose positions should be read.

        Returns
        -------
        list[ScalarAggregator]
            Aggregators for combined, horizontal, and vertical BPM positions.
        """
        agg = BPMScalarAggregator(self.get_lattice())
        aggh = BPMHScalarAggregator(self.get_lattice())
        aggv = BPMVScalarAggregator(self.get_lattice())
        for b in bpms:
            e = self.get_at_elems(b)[0]
            agg.add_elem(e)
            aggh.add_elem(e)
            aggv.add_elem(e)
        return [agg, aggh, aggv]

    def _fill_magnet(self, magnet: Magnet) -> None:
        current = (
            RWHardwareScalar(self.get_at_elems(magnet), magnet.polynom, magnet.model) if magnet.model.has_physics() else None
        )
        strength = (
            RWStrengthScalar(self.get_at_elems(magnet), magnet.polynom, magnet.model) if magnet.model.has_physics() else None
        )
        self.magnet.add(magnet.attach(self, strength, current))

    def _fill_combined_function_magnet(self, magnet: CombinedFunctionMagnet) -> None:
        currents = (
            RWHardwareArray(self.get_at_elems(magnet), magnet.polynoms, magnet.model) if magnet.model.has_physics() else None
        )
        strengths = (
            RWStrengthArray(self.get_at_elems(magnet), magnet.polynoms, magnet.model) if magnet.model.has_physics() else None
        )
        magnets = magnet.attach(self, strengths, currents)
        self.combined_function_magnet.add(magnets[0])
        for virtual_magnet in magnets[1:]:
            self.magnet.add(virtual_magnet)

    def _fill_serialized_magnets(self, magnets: SerializedMagnets) -> None:
        currents = []
        strengths = []
        for index, magnet in enumerate(magnets.get_magnets()):
            current = (
                RWHardwareScalar(self.get_at_elems(magnet), magnets.polynom, magnets.model.get_sub_model(index))
                if magnets.model.has_hardware()
                else None
            )
            strength = (
                RWStrengthScalar(self.get_at_elems(magnet), magnets.polynom, magnets.model.get_sub_model(index))
                if magnets.model.has_physics()
                else None
            )
            currents.append(current)
            strengths.append(strength)
        linked_currents = []
        linked_strengths = []
        for index in range(magnets.get_nb_magnets()):
            linked_currents.append(RWSerializedHardware(currents, index) if magnets.model.has_hardware() else None)
            linked_strengths.append(RWSerializedStrength(strengths, currents, index) if magnets.model.has_physics() else None)
        attached_magnets = magnets.attach(self, linked_strengths, linked_currents)
        self.serialized_magnet.add(attached_magnets[0])
        for magnet in attached_magnets[1:]:
            self.magnet.add(magnet)

    def _fill_bpm(self, bpm: BPM) -> None:
        bpm_elt = self.get_at_elems(bpm)[0]
        if not hasattr(bpm_elt, "Tilt"):
            bpm_elt.Tilt = 0.0
        if not hasattr(bpm_elt, "Offset"):
            bpm_elt.Offset = [0.0, 0.0]
        if len(bpm_elt.Offset) != 2:
            raise PyAMLException(f"BPM {bpm.get_name()} offset must be a 2-element array.")
        update_bpm_transform_matrix(bpm_elt)
        self.bpm.add(bpm.attach(self, RBpmArray(bpm_elt, self.ring), RWBpmOffsetArray(bpm_elt), RWBpmTiltScalar(bpm_elt)))

    def _fill_rf_plant(self, rf_plant: RFPlant) -> None:
        if rf_plant.transmitters:
            cavities: list[at.Element] = []
            harmonics: list[float] = []
            attached_transmitters: list[RFTransmitter] = []
            for transmitter in rf_plant.transmitters:
                transmitter_cavities: list[at.Element] = []
                for cavity_name in transmitter.cavities:
                    cavity = self.get_at_elems(Element(cavity_name))
                    if len(cavity) > 1:
                        raise PyAMLException(f"RF transmitter {transmitter.get_name()},multiple cavity definition:{{cav[0]}}")
                    if len(cavity) == 0:
                        raise PyAMLException(f"RF transmitter {transmitter.get_name()}, No cavity found")
                    transmitter_cavities.append(cavity[0])
                    harmonics.append(transmitter.harmonic)
                voltage = RWRFVoltageScalar(transmitter_cavities)
                phase = RWRFPhaseScalar(transmitter_cavities)
                attached_transmitter = transmitter.attach(self, voltage, phase)
                self.rf.transmitter.add(attached_transmitter)
                cavities.extend(transmitter_cavities)
                attached_transmitters.append(attached_transmitter)
            self.rf.add(rf_plant.attach(self, RWRFFrequencyScalar(cavities, harmonics), RWTotalVoltage(attached_transmitters)))
        else:
            self.rf.add(rf_plant.attach(self, RWRFATFrequencyScalar(self.ring), RWRFATotalVoltageScalar(self.ring)))

    def _fill_betatron_tune_monitor(self, monitor: BetatronTuneMonitor) -> None:
        self.add_betatron_tune_monitor(monitor.attach(self, RBetatronTuneArray(self.ring)))

    def _fill_tool(self, tool: TuningTool | MeasurementTool) -> None:
        self.add_tool(tool.attach(self))

    def _fill_unbound_element(self, element: "UnboundElement") -> None:
        pass

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
        """
        Resolve a PyAML element to matching PyAT lattice elements.

        Parameters
        ----------
        element : Element
            PyAML element whose lattice mapping should be resolved.

        Returns
        -------
        list[at.Element]
            Matching Accelerator Toolbox lattice elements.
        """
        if self._linker:
            identifier = self._linker.get_element_identifier(element)
            element_list = self._linker.get_at_elements(identifier)
            if not element_list:
                raise PyAMLException(f"{identifier} not found in lattice:{self._cfg.lattice}")
            return element_list
        else:
            # By list
            nameList = self.get_names(element)

            if nameList is not None:
                names = []
                for name in nameList:
                    if name not in self._elements_indexing:
                        raise PyAMLException(f"{name} not found in lattice:{self._cfg.lattice}")
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
                    raise PyAMLException(f"{name} not found in lattice:{self._cfg.lattice}")
                elts = self._elements_indexing[name]
                if indices is None:
                    return elts
                else:
                    return [elts[idx] for idx in indices]

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
