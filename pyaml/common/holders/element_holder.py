"""
Module handling element references for simulators and control system
"""

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
    from ...tuning_tools.bba import BBA
    from ...tuning_tools.chromaticity import Chromaticity
    from ...tuning_tools.chromaticity_response_matrix import ChromaticityResponseMatrix
    from ...tuning_tools.dispersion import Dispersion
    from ...tuning_tools.orbit import Orbit
    from ...tuning_tools.orbit_response_matrix import OrbitResponseMatrix
    from ...tuning_tools.tune import Tune
    from ...tuning_tools.tune_response_matrix import TuneResponseMatrix


class ElementHolder(metaclass=ABCMeta):
    """
    Class that store references of objects used from both
    simulators and control system
    """

    def __init__(self):
        # Device handle
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
        """
        Returns the peer accelerator of this holder
        """
        return self._peer

    # Sub holders ----------------------------------------------------------------

    @property
    def magnet(self) -> MagnetHolder:
        return self._magnet_holder

    @property
    def magnets(self) -> MagnetsHolder:
        return self._magnets_holder

    @property
    def serialized_magnet(self) -> SerializedMagnetHolder:
        return self._serialized_magnet_holder

    @property
    def serialized_magnets(self) -> SerializedMagnetsHolder:
        return self._serialized_magnets_holder

    @property
    def combined_function_magnet(self) -> CombinedFunctionMagnetHolder:
        return self._combined_function_magnet_holder

    @property
    def combined_function_magnets(self) -> CombinedFunctionMagnetsHolder:
        return self._combined_function_magnets_holder

    @property
    def bpm(self) -> BPMHolder:
        return self._bpm_holder

    @property
    def bpms(self) -> BPMsHolder:
        return self._bpms_holder

    @property
    def rf(self) -> RFHolder:
        return self._rf_holder

    def post_init(self):
        """
        Method triggered after all initialisations are done
        """
        for e in self.get_all_elements():
            e.post_init()

    def fill_device(self, elements: list[Element]):
        raise PyAMLException("ElementHolder.fill_device() is not subclassed")

    # Aggregators

    @abstractmethod
    def create_magnet_strength_aggregator(self, magnets: list[Magnet]) -> ScalarAggregator | None:
        pass

    @abstractmethod
    def create_magnet_hardware_aggregator(self, magnets: list[Magnet]) -> ScalarAggregator | None:
        pass

    @abstractmethod
    def create_bpm_aggregators(self, bpms: list[BPM]) -> list[ScalarAggregator | None]:
        pass

    # Elements

    def find_elements(self, filter: str) -> list[str]:
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
        if element.get_name() in self._ALL:  # Ensure name unicity
            raise PyAMLException(f"Duplicate element {element.__class__.__name__} name {{element.get_name()}}") from None
        array[element.get_name()] = element
        self._ALL[element.get_name()] = element

    def _get(self, what, name, array) -> Element:
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
        self._fill_array(
            arrayName,
            elementNames,
            self.get_element,
            ElementArray,
            self._ELEMENT_ARRAYS,
        )

    def add_element(self, element: Element):
        self._ALL[element.get_name()] = element

    def get_element(self, name: str) -> Element:
        return self._get("Element", name, self._ALL)

    def get_elements(self, name: str) -> ElementArray:
        return self._get("Element array", name, self._ELEMENT_ARRAYS)

    def get_all_elements(self) -> list[Element]:
        return [value for key, value in self._ALL.items()]

    # Tune monitor

    def get_betatron_tune_monitor(self, name: str) -> BetatronTuneMonitor:
        return self._get("Diagnostic", name, self._DIAG)

    def add_betatron_tune_monitor(self, tune_monitor: Element):
        self._add(self._DIAG, tune_monitor)

    # Tuning/Measurement tools

    def add_tool(self, tool: Element):
        self._add(self._TOOLS, tool)

    # ---- Chromaticity -------------------------------------------------

    def get_chromaticity_monitor(self, name: str) -> ChromaticityMonitor:
        obj = self._get("Chromaticity monitor", name, self._TOOLS)
        return obj

    def get_chromaticity_tuning(self, name: str) -> "Chromaticity":
        return self._get("Chromaticity tool", name, self._TOOLS)

    def get_crm_tuning(self, name: str) -> "ChromaticityResponseMatrix":
        return self._get("ChromaticityResponseMatrix tool", name, self._TOOLS)

    @property
    def chromaticity(self) -> "Chromaticity":
        return self.get_chromaticity_tuning("DEFAULT_CHROMATICITY_CORRECTION")

    @property
    def crm(self) -> "ChromaticityResponseMatrix":
        return self.get_crm_tuning("DEFAULT_CHROMATICITY_RESPONSE_MATRIX")

    # ---- Tune ---------------------------------------------------------

    def get_tune_tuning(self, name: str) -> "Tune":
        return self._get("Tune tuning tool", name, self._TOOLS)

    @property
    def tune(self) -> "Tune":
        return self.get_tune_tuning("DEFAULT_TUNE_CORRECTION")

    def get_trm_tuning(self, name: str) -> "TuneResponseMatrix":
        return self._get("TuneResponseMatrix tool", name, self._TOOLS)

    @property
    def trm(self) -> "TuneResponseMatrix":
        return self.get_trm_tuning("DEFAULT_TUNE_RESPONSE_MATRIX")

    # ---- Orbit --------------------------------------------------------

    def get_orbit_tuning(self, name: str) -> "Orbit":
        return self._get("Orbit tuning tool", name, self._TOOLS)

    @property
    def orbit(self) -> "Orbit":
        return self.get_orbit_tuning("DEFAULT_ORBIT_CORRECTION")

    def get_orm_tuning(self, name: str) -> "OrbitResponseMatrix":
        return self._get("OrbitResponseMatrix tool", name, self._TOOLS)

    @property
    def orm(self) -> "OrbitResponseMatrix":
        return self.get_orm_tuning("DEFAULT_ORBIT_RESPONSE_MATRIX")

    # ---- BBA --------------------------------------------------------

    def get_bba(self, name: str) -> "BBA":
        return self._get("BBA tool", name, self._TOOLS)

    # ---- Dispersive orbit --------------------------------------------

    def get_dispersion_tuning(self, name: str) -> "Dispersion":
        return self._get("Dispersion tool", name, self._TOOLS)

    @property
    def dispersion(self) -> "Dispersion":
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
