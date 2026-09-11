"""Store, resolve, and group elements shared by runtime backends."""

import fnmatch
import re
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, overload

from ...arrays.element_array import ElementArray
from ...bpm.bpm import BPM
from ...diagnostics.tune_monitor import BetatronTuneMonitor
from ...magnet.cfm_magnet import CombinedFunctionMagnet
from ...magnet.magnet import Magnet
from ...magnet.serialized_magnet import SerializedMagnets
from ...rf.rf_plant import RFPlant
from ...rf.rf_transmitter import RFTransmitter
from ...tuning_tools.chromaticity_monitor import ChromaticityMonitor
from ..abstract_aggregator import ScalarAggregator
from ..element import Element
from ..exception import PyAMLException
from .rf_holder import RFHolder
from .sub_holders import (
    BPMHolder,
    BPMsHolder,
    CombinedFunctionMagnetHolder,
    CombinedFunctionMagnetsHolder,
    MagnetHolder,
    MagnetsHolder,
    SerializedMagnetHolder,
    SerializedMagnetsHolder,
)

if TYPE_CHECKING:
    from ...accelerator import Accelerator
    from ...configuration.unbound_element import UnboundElement
    from ...tuning_tools.bba import BBA
    from ...tuning_tools.chromaticity import Chromaticity
    from ...tuning_tools.chromaticity_response_matrix import ChromaticityResponseMatrix
    from ...tuning_tools.dispersion import Dispersion
    from ...tuning_tools.measurement_tool import MeasurementTool
    from ...tuning_tools.orbit import Orbit
    from ...tuning_tools.orbit_response_matrix import OrbitResponseMatrix
    from ...tuning_tools.tune import Tune
    from ...tuning_tools.tune_response_matrix import TuneResponseMatrix
    from ...tuning_tools.tuning_tool import TuningTool


class ElementHolder(metaclass=ABCMeta):
    """
    Manage named elements, diagnostics, tools, and element arrays.

    An element holder owns every element of one accelerator mode and exposes them
    through per-type accessors. :class:`~pyaml.control.controlsystem.ControlSystem`
    and :class:`~pyaml.lattice.simulator.Simulator` both derive from it, so the same
    API drives a live machine and a simulation.

    Attributes
    ----------
    magnet, magnets
        Single magnet by name, or a named magnet array.
    bpm, bpms
        Single BPM by name, or a named BPM array.
    combined_function_magnet, combined_function_magnets
        Single combined-function magnet by name, or a named array.
    serialized_magnet, serialized_magnets
        Single serialized magnet group by name, or a named array.
    rf
        RF plant and transmitters of this mode.
    tune, chromaticity, orbit, dispersion
        Tuning tools attached to this mode, looked up by name.
    trm, crm, orm
        Response-matrix measurement tools, looked up by name.

    Methods
    -------
    post_init()
        Run post-initialization hooks for every stored element.
    fill_device(elements)
        Bind configured elements to the holder's runtime backend.
    create_magnet_strength_aggregator(magnets)
        Create an aggregator exposing the selected magnets' strengths.
    create_magnet_hardware_aggregator(magnets)
        Create an aggregator exposing the selected hardware values.
    create_bpm_aggregators(bpms)
        Create aggregate BPM position interfaces.
    find_elements(filter)
        Find element names matching a literal, wildcard, or regular expression.
    fill_element_array(arrayName, elementNames)
        Create and register a generic element array.
    add_element(element)
        Add an element to the global element store.
    get_element(name)
        Return a named element from the global store.
    get_elements(name)
        Return a named generic element array.
    get_all_elements()
        Return all registered elements in insertion order.
    get_betatron_tune_monitor(name)
        Return a named betatron tune monitor.
    add_betatron_tune_monitor(tune_monitor)
        Add a betatron tune monitor to the diagnostics store.
    add_tool(tool)
        Add a tuning or measurement tool to the tool store.
    get_chromaticity_monitor(name)
        Return a named chromaticity monitor.
    get_chromaticity_tuning(name)
        Return a named chromaticity tuning tool.
    get_crm_tuning(name)
        Return a named chromaticity response-matrix tool.
    get_tune_tuning(name)
        Return a named tune correction tool.
    get_trm_tuning(name)
        Return a named tune response-matrix tool.
    get_orbit_tuning(name)
        Return a named orbit correction tool.
    get_orm_tuning(name)
        Return a named orbit response-matrix tool.
    get_bba(name)
        Return a named beam-based alignment tool.
    get_dispersion_tuning(name)
        Return a named dispersion tuning tool.
    """

    def __init__(self):
        # Device handle
        """Initialize empty element stores and typed sub-holders."""
        self._MAGNETS: dict[str, Magnet] = {}
        self._CFM_MAGNETS: dict[str, CombinedFunctionMagnet] = {}
        self._SERIALIZED_MAGNETS: dict[str, SerializedMagnets] = {}
        self._BPMS: dict[str, BPM] = {}
        self._RFPLANT: dict[str, RFPlant] = {}
        self._RFTRANSMITTER: dict[str, RFTransmitter] = {}
        self._DIAG: dict[str, Element] = {}
        self._TOOLS: dict[str, Element] = {}
        self._ALL: dict[str, Element] = {}

        self.__by_class_elements: dict[type, dict] = {
            Magnet: self._MAGNETS,
            CombinedFunctionMagnet: self._CFM_MAGNETS,
            SerializedMagnets: self._SERIALIZED_MAGNETS,
            BPM: self._BPMS,
            RFPlant: self._RFPLANT,
            RFTransmitter: self._RFTRANSMITTER,
        }

        # Array handle
        self._MAGNET_ARRAYS: dict = {}
        self._CFM_MAGNET_ARRAYS: dict = {}
        self._SERIALIZED_MAGNETS_ARRAYS: dict = {}
        self._BPM_ARRAYS: dict = {}
        self._ELEMENT_ARRAYS: dict = {}

        # Sub holders
        self._magnet_holder = MagnetHolder(self)
        self._magnets_holder = MagnetsHolder(self)
        self._serialized_magnet_holder = SerializedMagnetHolder(self)
        self._serialized_magnets_holder = SerializedMagnetsHolder(self)
        self._combined_function_magnet_holder = CombinedFunctionMagnetHolder(self)
        self._combined_function_magnets_holder = CombinedFunctionMagnetsHolder(self)
        self._bpm_holder = BPMHolder(self)
        self._bpms_holder = BPMsHolder(self)
        self._rf_holder = RFHolder(self)

    @property
    def peer(self) -> "Accelerator":
        """Return the accelerator associated with this holder."""
        return self._peer

    # Sub holders ----------------------------------------------------------------

    @property
    def magnet(self) -> MagnetHolder:
        """Return the magnet."""
        return self._magnet_holder

    @property
    def magnets(self) -> MagnetsHolder:
        """Return the magnets."""
        return self._magnets_holder

    @property
    def serialized_magnet(self) -> SerializedMagnetHolder:
        """Return the serialized magnet."""
        return self._serialized_magnet_holder

    @property
    def serialized_magnets(self) -> SerializedMagnetsHolder:
        """Return the serialized magnets."""
        return self._serialized_magnets_holder

    @property
    def combined_function_magnet(self) -> CombinedFunctionMagnetHolder:
        """Return the combined function magnet."""
        return self._combined_function_magnet_holder

    @property
    def combined_function_magnets(self) -> CombinedFunctionMagnetsHolder:
        """Return the combined function magnets."""
        return self._combined_function_magnets_holder

    @property
    def bpm(self) -> BPMHolder:
        """Return the bpm."""
        return self._bpm_holder

    @property
    def bpms(self) -> BPMsHolder:
        """Return the bpms."""
        return self._bpms_holder

    @property
    def rf(self) -> RFHolder:
        """Return the rf."""
        return self._rf_holder

    def post_init(self):
        """Run post-initialization hooks for every stored element."""
        for e in self.get_all_elements():
            e.post_init()

    def fill_device(self, elements: list[Element]):
        for element in elements:
            element._fill_device(self)

    @abstractmethod
    def _fill_magnet(self, magnet: Magnet) -> None:
        pass

    @abstractmethod
    def _fill_combined_function_magnet(self, magnet: CombinedFunctionMagnet) -> None:
        pass

    @abstractmethod
    def _fill_serialized_magnets(self, magnets: SerializedMagnets) -> None:
        pass

    @abstractmethod
    def _fill_bpm(self, bpm: BPM) -> None:
        pass

    @abstractmethod
    def _fill_rf_plant(self, rf_plant: RFPlant) -> None:
        pass

    @abstractmethod
    def _fill_betatron_tune_monitor(self, monitor: BetatronTuneMonitor) -> None:
        pass

    @abstractmethod
    def _fill_tool(self, tool: "TuningTool | MeasurementTool") -> None:
        pass

    @abstractmethod
    def _fill_unbound_element(self, element: "UnboundElement") -> None:
        pass

    # Aggregators

    @abstractmethod
    def create_magnet_strength_aggregator(self, magnets: list[Magnet]) -> ScalarAggregator | None:
        """
        Create an aggregator exposing the selected magnets' strengths.

        Parameters
        ----------
        magnets : list[Magnet]
            Magnets to include in the strength aggregator.

        Returns
        -------
        ScalarAggregator | None
            Strength aggregator, or ``None`` when unsupported.
        """
        pass

    @abstractmethod
    def create_magnet_hardware_aggregator(self, magnets: list[Magnet]) -> ScalarAggregator | None:
        """
        Create an aggregator exposing the selected hardware values.

        Parameters
        ----------
        magnets : list[Magnet]
            Magnets to include in the hardware aggregator.

        Returns
        -------
        ScalarAggregator | None
            Hardware aggregator, or ``None`` when unsupported.
        """
        pass

    @abstractmethod
    def create_bpm_aggregators(self, bpms: list[BPM]) -> list[ScalarAggregator | None]:
        """
        Create aggregate BPM position interfaces.

        Parameters
        ----------
        bpms : list[BPM]
            BPMs to include in the aggregators.

        Returns
        -------
        list[ScalarAggregator | None]
            Aggregators for combined, horizontal, and vertical positions.
        """
        pass

    # Elements

    def find_elements(self, filter: str) -> list[str]:
        """
        Find element names matching a literal, wildcard, or regular expression.

        Parameters
        ----------
        filter : str
            Pattern to match. Prefix with ``re:`` for a regular expression.

        Returns
        -------
        list[str]
            Matching element names.
        """
        if filter.startswith("re:"):
            pattern = re.compile(rf"{filter[3:]}")
            elements = [k for k in self._ALL.keys() if pattern.fullmatch(k)]
        elif "*" in filter or "?" in filter:
            elements = [k for k in self._ALL.keys() if fnmatch.fnmatch(k, filter)]
        else:
            elements = [filter]

        return elements

    def _fill_array(
        self,
        array_name: str,
        element_names: list[str],
        get_func,
        constructor,
        ARR: dict,
    ):
        # Handle wildcard, regexp and exclusion pattern
        """
        Resolve selectors and store a constructed element array.

        Parameters
        ----------
        array_name : str
            Name of the array to create.
        element_names : list[str]
            Element names or selectors; prefix with ``~`` to exclude matches.
        get_func : object
            Callback used to resolve element names.
        constructor : object
            Constructor for the resulting array.
        ARR : dict
            Destination array store.
        """
        all_names: list[str] = []
        excluded_names: list[str] = []
        for name in element_names:
            if name.startswith("~"):
                names = self.find_elements(name[1:])
                excluded_names.extend(names)
            else:
                names = self.find_elements(name)
                all_names.extend(names)

        [all_names.remove(name) for name in excluded_names]

        a = []
        for n in all_names:
            try:
                m = get_func(n)
            except Exception as err:
                raise PyAMLException(f"{constructor.__name__} {array_name} : {err} @index {len(a)}") from None
            if m in a:
                raise PyAMLException(f"{constructor.__name__} {array_name} : duplicate name {name} @index {len(a)}") from None
            a.append(m)
        ARR[array_name] = constructor(array_name, a)

    def _add(self, array, element: Element):
        """
        Register an element in a typed store and the global index.

        Parameters
        ----------
        array : object
            Destination typed store.
        element : Element
            Element to register.
        """
        if element.get_name() in self._ALL:  # Ensure name unicity
            raise PyAMLException(f"Duplicate element {element.__class__.__name__} name {{element.get_name()}}") from None
        array[element.get_name()] = element
        self._ALL[element.get_name()] = element

    def _get(self, what, name, array) -> Element:
        """
        Return a named object from a typed store.

        Parameters
        ----------
        what : object
            Object type used in lookup errors.
        name : object
            Name to look up.
        array : object
            Name-indexed store to search.

        Returns
        -------
        Element
            Object registered under ``name``.
        """
        if name not in array:
            raise PyAMLException(f"{what} {name} not defined")
        return array[name]

    # Generic elements
    def get(self) -> ElementArray:
        """Return all registered elements in insertion order.

        Returns
        -------
        ElementArray
            New unnamed container sharing the registered element references.

        Notes
        -----
        Registration order is not necessarily longitudinal lattice order.
        Changing the returned container does not change the holder registry.
        Each call reflects the current registry.

        Examples
        --------
        >>> elements = sr.live.get()
        >>> names = elements.names()
        """
        return ElementArray("", list(self._ALL.values()))

    @overload
    def __getitem__(self, key: int) -> Element: ...

    @overload
    def __getitem__(self, key: slice) -> ElementArray: ...

    @overload
    def __getitem__(self, key: str) -> Element | ElementArray | None: ...

    def __getitem__(self, key: int | slice | str) -> Element | ElementArray | None:
        """Retrieve an element or select a collection.

        Parameters
        ----------
        key : int, slice or str
            Index in registration order, slice, exact name, or name pattern.
            Strings containing ``*``, ``?`` or ``[`` use fnmatch matching.
            Other strings are exact registry keys. Colons are literal.

        Returns
        -------
        Element or ElementArray or None
            An index returns an element. An exact name returns its element
            or None. Patterns and slices return the most specific compatible
            array, or an empty ElementArray when nothing matches.
            The full slice ``[:]`` returns a generic ElementArray, like get().

        Raises
        ------
        IndexError
            If the index is out of bounds.
        TypeError
            If the key is neither an integer, a slice, nor a string.
        ValueError
            If a slice has a zero step.

        Notes
        -----
        Indices follow insertion order, not necessarily lattice order.
        Collections share element references but do not modify the registry.
        Field filters and regular expressions are not interpreted here.

        Examples
        --------
        >>> bpm = sr.live["BPM01"]
        >>> missing = sr.live["UNKNOWN"]  # None
        >>> bpms = sr.live["BPM*"]
        >>> bpms = sr.live["BPM0[123]"]  # BPM01, BPM02 or BPM03
        >>> bpms = sr.live["BPM0[1-3]"]  # Same selection using a range
        >>> quads = sr.live["Q[FD]*"]  # Names starting with QF or QD
        >>> bpms = sr.live["BPM0[!3]"]  # One character after BPM0, except 3
        >>> first = sr.live[0]
        >>> subset = sr.live[1:10]
        >>> all_elements = sr.live[:]
        """
        if isinstance(key, str):
            if any(marker in key for marker in "*?["):
                return self.get()._select_names(key)
            return self._ALL.get(key)
        if isinstance(key, int):
            return list(self._ALL.values())[key]
        if isinstance(key, slice):
            elements = self.get()
            if key == slice(None):
                return elements
            return elements._typed_array(list(elements)[key])
        raise TypeError("ElementHolder keys must be integers, slices or strings")

    def fill_element_array(self, arrayName: str, elementNames: list[str]):
        """
        Create and register a generic element array.

        Parameters
        ----------
        arrayName : str
            Name under which the new array is registered.
        elementNames : list[str]
            Names of the elements to gather into the array, in the order they should appear.
        """
        self._fill_array(
            arrayName,
            elementNames,
            self.get_element,
            ElementArray,
            self._ELEMENT_ARRAYS,
        )

    def add_element(self, element: Element):
        """
        Add an element to the global element store.

        Parameters
        ----------
        element : Element
            Element to register, keyed by its own name.
        """
        self._ALL[element.get_name()] = element

    def get_element(self, name: str) -> Element:
        """
        Return a named element from the global store.

        Parameters
        ----------
        name : str
            Name of the element to look up, as declared in the configuration.

        Returns
        -------
        Element
            The element registered under ``name``.
        """
        return self._get("Element", name, self._ALL)

    def get_elements(self, name: str) -> ElementArray:
        """
        Return a named generic element array.

        Parameters
        ----------
        name : str
            Name of the element array to look up, as declared in the configuration.

        Returns
        -------
        ElementArray
            The element array registered under ``name``.
        """
        return self._get("Element array", name, self._ELEMENT_ARRAYS)

    def get_all_elements(self) -> list[Element]:
        """Return all registered elements in insertion order."""
        return [value for key, value in self._ALL.items()]

    # Tune monitor

    def get_betatron_tune_monitor(self, name: str) -> BetatronTuneMonitor:
        """
        Return a named betatron tune monitor.

        Parameters
        ----------
        name : str
            Name of the betatron tune monitor to look up, as declared in the configuration.

        Returns
        -------
        BetatronTuneMonitor
            The betatron tune monitor registered under ``name``.
        """
        return self._get("Diagnostic", name, self._DIAG)

    def add_betatron_tune_monitor(self, tune_monitor: Element):
        """
        Add a betatron tune monitor to the diagnostics store.

        Parameters
        ----------
        tune_monitor : Element
            Betatron tune monitor to register, keyed by its own name.
        """
        self._add(self._DIAG, tune_monitor)

    # Tuning/Measurement tools

    def add_tool(self, tool: Element):
        """
        Add a tuning or measurement tool to the tool store.

        Parameters
        ----------
        tool : Element
            Tuning or measurement tool to register, keyed by its own name.
        """
        self._add(self._TOOLS, tool)

    # ---- Chromaticity -------------------------------------------------

    def get_chromaticity_monitor(self, name: str) -> ChromaticityMonitor:
        """
        Return a named chromaticity monitor.

        Parameters
        ----------
        name : str
            Name of the chromaticity monitor to look up, as declared in the configuration.

        Returns
        -------
        ChromaticityMonitor
            The chromaticity monitor registered under ``name``.
        """
        obj = self._get("Chromaticity monitor", name, self._TOOLS)
        return obj

    def get_chromaticity_tuning(self, name: str) -> "Chromaticity":
        """
        Return a named chromaticity tuning tool.

        Parameters
        ----------
        name : str
            Name of the chromaticity tuning tool to look up, as declared in the configuration.

        Returns
        -------
        'Chromaticity'
            The chromaticity tuning tool registered under ``name``.
        """
        return self._get("Chromaticity tool", name, self._TOOLS)

    def get_crm_tuning(self, name: str) -> "ChromaticityResponseMatrix":
        """
        Return a named chromaticity response-matrix tool.

        Parameters
        ----------
        name : str
            Name of the chromaticity response-matrix tool to look up, as declared in the configuration.

        Returns
        -------
        'ChromaticityResponseMatrix'
            The chromaticity response-matrix tool registered under ``name``.
        """
        return self._get("ChromaticityResponseMatrix tool", name, self._TOOLS)

    @property
    def chromaticity(self) -> "Chromaticity":
        """Return the chromaticity."""
        return self.get_chromaticity_tuning("DEFAULT_CHROMATICITY_CORRECTION")

    @property
    def crm(self) -> "ChromaticityResponseMatrix":
        """Return the crm."""
        return self.get_crm_tuning("DEFAULT_CHROMATICITY_RESPONSE_MATRIX")

    # ---- Tune ---------------------------------------------------------

    def get_tune_tuning(self, name: str) -> "Tune":
        """
        Return a named tune correction tool.

        Parameters
        ----------
        name : str
            Name of the tune correction tool to look up, as declared in the configuration.

        Returns
        -------
        'Tune'
            The tune correction tool registered under ``name``.
        """
        return self._get("Tune tuning tool", name, self._TOOLS)

    @property
    def tune(self) -> "Tune":
        """Return the tune."""
        return self.get_tune_tuning("DEFAULT_TUNE_CORRECTION")

    def get_trm_tuning(self, name: str) -> "TuneResponseMatrix":
        """
        Return a named tune response-matrix tool.

        Parameters
        ----------
        name : str
            Name of the tune response-matrix tool to look up, as declared in the configuration.

        Returns
        -------
        'TuneResponseMatrix'
            The tune response-matrix tool registered under ``name``.
        """
        return self._get("TuneResponseMatrix tool", name, self._TOOLS)

    @property
    def trm(self) -> "TuneResponseMatrix":
        """Return the default tune response-matrix tool."""
        return self.get_trm_tuning("DEFAULT_TUNE_RESPONSE_MATRIX")

    # ---- Orbit --------------------------------------------------------

    def get_orbit_tuning(self, name: str) -> "Orbit":
        """
        Return a named orbit correction tool.

        Parameters
        ----------
        name : str
            Name of the orbit correction tool to look up, as declared in the configuration.

        Returns
        -------
        'Orbit'
            The orbit correction tool registered under ``name``.
        """
        return self._get("Orbit tuning tool", name, self._TOOLS)

    @property
    def orbit(self) -> "Orbit":
        """Return the orbit."""
        return self.get_orbit_tuning("DEFAULT_ORBIT_CORRECTION")

    def get_orm_tuning(self, name: str) -> "OrbitResponseMatrix":
        """
        Return a named orbit response-matrix tool.

        Parameters
        ----------
        name : str
            Name of the orbit response-matrix tool to look up, as declared in the configuration.

        Returns
        -------
        'OrbitResponseMatrix'
            The orbit response-matrix tool registered under ``name``.
        """
        return self._get("OrbitResponseMatrix tool", name, self._TOOLS)

    @property
    def orm(self) -> "OrbitResponseMatrix":
        """Return the default orbit response-matrix tool."""
        return self.get_orm_tuning("DEFAULT_ORBIT_RESPONSE_MATRIX")

    # ---- BBA --------------------------------------------------------

    def get_bba(self, name: str) -> "BBA":
        """
        Return a named beam-based alignment tool.

        Parameters
        ----------
        name : str
            Name of the beam-based alignment tool to look up, as declared in the configuration.

        Returns
        -------
        'BBA'
            The beam-based alignment tool registered under ``name``.
        """
        return self._get("BBA tool", name, self._TOOLS)

    # ---- Dispersive orbit --------------------------------------------

    def get_dispersion_tuning(self, name: str) -> "Dispersion":
        """
        Return a named dispersion tuning tool.

        Parameters
        ----------
        name : str
            Name of the dispersion tuning tool to look up, as declared in the configuration.

        Returns
        -------
        'Dispersion'
            The dispersion tuning tool registered under ``name``.
        """
        return self._get("Dispersion tool", name, self._TOOLS)

    @property
    def dispersion(self) -> "Dispersion":
        """Return the dispersion."""
        return self.get_dispersion_tuning("DEFAULT_DISPERSION")

    def _get_array(self, name: str):
        """
        Generic array resolver used by YellowPages.

        The method returns the array object referenced by 'name', regardless of its
        concrete type.
        """
        if name in self._BPM_ARRAYS:
            return self._BPM_ARRAYS[name]
        if name in self._MAGNET_ARRAYS:
            return self._MAGNET_ARRAYS[name]
        if name in self._CFM_MAGNET_ARRAYS:
            return self._CFM_MAGNET_ARRAYS[name]
        if name in self._SERIALIZED_MAGNETS_ARRAYS:
            return self._SERIALIZED_MAGNETS_ARRAYS[name]
        if name in self._ELEMENT_ARRAYS:
            return self._ELEMENT_ARRAYS[name]

        raise PyAMLException(f"Array {name} not defined")

    def _get_tool(self, name: str):
        """
        Generic tuning tool resolver used by YellowPages.
        """
        if name not in self._TOOLS:
            raise PyAMLException(f"Tool {name} not defined")
        return self._TOOLS[name]

    def _get_diagnostic(self, name: str):
        """
        Generic diagnostic resolver used by YellowPages.
        """
        if name not in self._DIAG:
            raise PyAMLException(f"Diagnostic {name} not defined")
        return self._DIAG[name]

    def _list_arrays(self) -> list[str]:
        """
        Return all array identifiers available in this holder.
        """
        arrays: list[str] = []
        arrays.extend(self._BPM_ARRAYS.keys())
        arrays.extend(self._MAGNET_ARRAYS.keys())
        arrays.extend(self._CFM_MAGNET_ARRAYS.keys())
        arrays.extend(self._SERIALIZED_MAGNETS_ARRAYS.keys())
        arrays.extend(self._ELEMENT_ARRAYS.keys())
        return arrays

    def _list_tools(self) -> list[str]:
        """
        Return all tuning tool identifiers available in this holder.
        """
        return list(self._TOOLS.keys())

    def _list_diagnostics(self) -> list[str]:
        """
        Return all diagnostic identifiers available in this holder.
        """
        return list(self._DIAG.keys())

    def _set_energy(self, E: float):
        """
        Sets the energy on all elements

        Parameters
        ----------
        E : float
            Energy in eV
        """
        # Needed by energy dependant element (i.e. magnet coil current calculation)
        for m in self.get_all_elements():
            m.set_energy(E)

    def _set_mcf(self, alphac: float):
        """
        Sets the moment compaction factor on all elements

        Parameters
        ----------
        alphac : float
            Moment compaction factor
        """
        # Needed by some off energy dependant element (i.e. chromaticty tools)
        for m in self.get_all_elements():
            m.set_mcf(alphac)

    def _set_harmonic(self, h: int):
        """
        Sets the harmonic number (number of bucket) on elements

        Parameters
        ----------
        h : int
            Harmonic number
        """
        for m in self.get_all_elements():
            m.set_harmonic(h)
