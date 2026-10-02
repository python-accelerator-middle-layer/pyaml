"""Store, resolve, and group elements shared by runtime backends."""

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
from ..abstract_aggregator import ScalarAggregator
from ..element import Element
from ..exception import PyAMLException
from ..name_matching import is_wildcard, resolve_names
from .diagnostic_holder import DiagnosticHolder
from .rf_holder import RFHolder
from .sub_holders import (
    CombinedFunctionMagnetHolder,
    CombinedFunctionMagnetsHolder,
    MagnetHolder,
    MagnetsHolder,
    SerializedMagnetHolder,
    SerializedMagnetsHolder,
)
from .tool_holder import ToolHolder

if TYPE_CHECKING:
    from ...accelerator import Accelerator
    from ...configuration.unbound_element import UnboundElement
    from ...tuning_tools.measurement_tool import MeasurementTool
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
    combined_function_magnet, combined_function_magnets
        Single combined-function magnet by name, or a named array.
    serialized_magnet, serialized_magnets
        Single serialized magnet group by name, or a named array.
    rf
        RF plant and transmitters of this mode.
    diagnostic
        Diagnostics of this mode, with typed default-name access.
    tool
        Tuning and measurement tools of this mode, with typed default-name access.

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
    get(name=None)
        Return a named element array, or every registered element when no name is given.
    add_betatron_tune_monitor(tune_monitor)
        Add a betatron tune monitor to the diagnostics store.
    add_tool(tool)
        Add a tuning or measurement tool to the tool store.
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
        self._rf_holder = RFHolder(self)
        self._diagnostic_holder = DiagnosticHolder(self)
        self._tool_holder = ToolHolder(self)

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
    def rf(self) -> RFHolder:
        """Return the rf."""
        return self._rf_holder

    @property
    def diagnostic(self) -> DiagnosticHolder:
        """Return the diagnostic."""
        return self._diagnostic_holder

    @property
    def tool(self) -> ToolHolder:
        """Return the tool."""
        return self._tool_holder

    def post_init(self):
        """Run post-initialization hooks for every stored element."""
        for e in self._ALL.values():
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

    def find_elements(self, filter: str | list[str] | tuple[str, ...]) -> list[str]:
        """
        Find element names matching one or several literal, wildcard, or regex patterns.

        Parameters
        ----------
        filter : str, list[str] or tuple[str, ...]
            Pattern, or patterns, to match. A pattern is a literal name, an
            fnmatch wildcard (``*``, ``?`` or ``[`` anywhere in the string),
            or a regular expression prefixed with ``re:``. Prefix any of
            those with ``~`` to exclude its matches instead, as in the
            ``elements:`` selector list of a YAML array declaration, e.g.
            ``["QD2*", "QF1*", "~QF1E-C05"]``. A lone ``~pattern`` (or a list
            made only of ``~`` entries) means "every element except those".

        Returns
        -------
        list[str]
            Matching element names.

        Raises
        ------
        PyAMLException
            If a literal pattern (or a ``~``-prefixed literal) matches no
            element, or a ``re:`` pattern is not a valid regular expression.
        """
        matched = set(resolve_names(self._ALL.keys(), filter, what="Element"))
        return [n for n in self._ALL if n in matched]

    def _fill_array(
        self,
        array_name: str,
        element_names: list[str],
        get_func,
        constructor,
        ARR: dict,
    ):
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
        excluded_names: set[str] = set()
        for name in element_names:
            if name.startswith("~"):
                excluded_names.update(self.find_elements(name[1:]))
            else:
                all_names.extend(self.find_elements(name))

        all_names = [n for n in all_names if n not in excluded_names]

        a = []
        for n in all_names:
            try:
                m = get_func(n)
            except Exception as err:
                raise PyAMLException(f"{constructor.__name__} {array_name} : {err} @index {len(a)}") from None
            if m in a:
                raise PyAMLException(f"{constructor.__name__} {array_name} : duplicate name {n} @index {len(a)}") from None
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
    def get(self, name: str | None = None) -> ElementArray:
        """Return a named element array, or every registered element when no name is given.

        Parameters
        ----------
        name : str, optional
            Name of the element array to look up, as declared in the configuration.
            When omitted, every registered element is returned instead.

        Returns
        -------
        ElementArray
            The element array registered under ``name``, regardless of its concrete
            family (magnet, BPM, combined-function magnet, serialized-magnet, or
            generic element array), or a new unnamed container of every registered
            element, in insertion order, when ``name`` is omitted.

        Raises
        ------
        PyAMLException
            If ``name`` is given and no array is registered under it.

        Notes
        -----
        Registration order is not necessarily longitudinal lattice order.
        Changing the returned container does not change the holder registry.
        Each call reflects the current registry.

        Examples
        --------
        >>> elements = sr.live.get()
        >>> names = elements.names()
        >>> cell08 = sr.live.get("CELL08")
        """
        if name is None:
            return ElementArray("", list(self._ALL.values()))
        return self._get_array(name)

    @overload
    def __getitem__(self, key: int) -> Element: ...

    @overload
    def __getitem__(self, key: slice) -> ElementArray: ...

    @overload
    def __getitem__(self, key: str) -> Element: ...

    @overload
    def __getitem__(self, key: list[str] | tuple[str, ...]) -> ElementArray: ...

    def __getitem__(self, key: int | slice | str | list[str] | tuple[str, ...]) -> Element | ElementArray:
        """Retrieve an element or select a collection.

        Parameters
        ----------
        key : int, slice, str, list[str] or tuple[str, ...]
            Index in registration order, slice, exact name, name pattern, or
            a list/tuple of patterns. Strings containing ``*``, ``?`` or
            ``[`` use fnmatch matching; a ``re:`` prefix uses a regular
            expression instead. Any other string is an exact registry key.
            Colons are literal. A list or tuple resolves each entry
            independently and unions the results. Prefix any pattern with
            ``~`` to exclude its matches instead, as in a YAML array's
            ``elements:`` list; a lone ``~pattern`` means every element
            except those matches.

        Returns
        -------
        Element or ElementArray
            An index or an exact literal name returns its element. Patterns,
            lists/tuples of patterns, and slices return the most specific
            compatible array, or an empty ElementArray when nothing matches.
            The full slice ``[:]`` returns a generic ElementArray, like get().

        Raises
        ------
        PyAMLException
            If an exact literal name, or a literal entry within a list or
            tuple, does not match any registered element, or if a ``re:``
            pattern is not a valid regular expression.
        IndexError
            If the index is out of bounds.
        TypeError
            If the key is neither an integer, a slice, a string, nor a
            list/tuple of strings.
        ValueError
            If a slice has a zero step.

        Notes
        -----
        Indices follow insertion order, not necessarily lattice order.
        Collections share element references but do not modify the registry.
        Field filters are not interpreted here.

        Examples
        --------
        >>> bpm = sr.live["BPM01"]
        >>> missing = sr.live["UNKNOWN"]  # raises PyAMLException
        >>> bpms = sr.live["BPM*"]
        >>> bpms = sr.live["BPM0[123]"]  # BPM01, BPM02 or BPM03
        >>> bpms = sr.live["BPM0[1-3]"]  # Same selection using a range
        >>> quads = sr.live["Q[FD]*"]  # Names starting with QF or QD
        >>> bpms = sr.live["BPM0[!3]"]  # One character after BPM0, except 3
        >>> bpms = sr.live["re:^BPM0[12]$"]  # Regular expression
        >>> mixed = sr.live[["BPM01", "QF1*"]]  # Union of several patterns
        >>> all_but_one = sr.live["~BPM01"]  # Every element except BPM01
        >>> most_quads = sr.live[["QF1*", "~QF1A-C01"]]  # QF1* minus one name
        >>> first = sr.live[0]
        >>> subset = sr.live[1:10]
        >>> all_elements = sr.live[:]
        """
        if isinstance(key, str):
            if key.startswith("re:") or key.startswith("~") or is_wildcard(key):
                matched = set(resolve_names(self._ALL.keys(), key))
                return self.get()._typed_array([v for n, v in self._ALL.items() if n in matched])
            if key not in self._ALL:
                raise PyAMLException(f"Element {key} not defined")
            return self._ALL[key]
        if isinstance(key, (list, tuple)):
            matched = set(resolve_names(self._ALL.keys(), key))
            return self.get()._typed_array([v for n, v in self._ALL.items() if n in matched])
        if isinstance(key, int):
            return list(self._ALL.values())[key]
        if isinstance(key, slice):
            elements = self.get()
            if key == slice(None):
                return elements
            return elements._typed_array(list(elements)[key])
        raise TypeError("ElementHolder keys must be integers, slices, strings, or lists/tuples of strings")

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
            self._get_element,
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

    def _get_element(self, name: str) -> Element:
        """
        Generic single-element resolver used internally to build element arrays.
        """
        return self._get("Element", name, self._ALL)

    # Tune monitor

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
        for m in self._ALL.values():
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
        for m in self._ALL.values():
            m.set_mcf(alphac)

    def _set_harmonic(self, h: int):
        """
        Sets the harmonic number (number of bucket) on elements

        Parameters
        ----------
        h : int
            Harmonic number
        """
        for m in self._ALL.values():
            m.set_harmonic(h)
