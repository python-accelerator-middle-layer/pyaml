"""
Module handling element references for simulators and control system
"""

import fnmatch
import re
from typing import TYPE_CHECKING

from ..arrays.bpm_array import BPMArray
from ..arrays.cfm_magnet_array import CombinedFunctionMagnetArray
from ..arrays.element_array import ElementArray
from ..arrays.magnet_array import MagnetArray
from ..arrays.serialized_magnet_array import SerializedMagnetsArray
from ..bpm.bpm import BPM
from ..common.exception import PyAMLException
from ..diagnostics.chromaticity_monitor import ChomaticityMonitor
from ..diagnostics.tune_monitor import BetatronTuneMonitor
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..magnet.magnet import Magnet
from ..magnet.serialized_magnet import SerializedMagnets
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter
from .element import Element

if TYPE_CHECKING:
    from ..tuning_tools.chromaticity import Chromaticity
    from ..tuning_tools.chromaticity_response_matrix import ChromaticityResponseMatrix
    from ..tuning_tools.dispersion import Dispersion
    from ..tuning_tools.orbit import Orbit
    from ..tuning_tools.orbit_response_matrix import OrbitResponseMatrix
    from ..tuning_tools.tune import Tune
    from ..tuning_tools.tune_response_matrix import TuneResponseMatrix


class ElementHolder(object):
    """
    Class that store references of objects used from both
    simulators and control system
    """

    def __init__(self):
        # Device handle
        self.__MAGNETS: dict[str, Magnet] = {}
        self.__CFM_MAGNETS: dict[str, CombinedFunctionMagnet] = {}
        self.__SERIALIZED_MAGNETS: dict[str, SerializedMagnets] = {}
        self.__BPMS: dict[str, BPM] = {}
        self.__RFPLANT: dict[str, RFPlant] = {}
        self.__RFTRANSMITTER: dict[str, RFTransmitter] = {}
        self.__DIAG: dict[str, Element] = {}
        self.__TUNING_TOOLS: dict[str, Element] = {}
        self.__ALL: dict[str, Element] = {}

        self.__by_class_elements: dict[type, dict] = {
            Magnet: self.__MAGNETS,
            CombinedFunctionMagnet: self.__CFM_MAGNETS,
            SerializedMagnets: self.__SERIALIZED_MAGNETS,
            BPM: self.__BPMS,
            RFPlant: self.__RFPLANT,
            RFTransmitter: self.__RFTRANSMITTER,
        }

        # Array handle
        self.__MAGNET_ARRAYS: dict = {}
        self.__CFM_MAGNET_ARRAYS: dict = {}
        self.__SERIALIZED_MAGNETS_ARRAYS: dict = {}
        self.__BPM_ARRAYS: dict = {}
        self.__ELEMENT_ARRAYS: dict = {}

    def post_init(self):
        """
        Method triggered after all initialisations are done
        """
        for e in self.get_all_elements():
            e.post_init()

    def fill_device(self, elements: list[Element]):
        raise PyAMLException("ElementHolder.fill_device() is not subclassed")

    def find_elements(self, filter: str) -> list[str]:
        if filter.startswith("re:"):
            pattern = re.compile(rf"{filter[3:]}")
            elements = [k for k in self.__ALL.keys() if pattern.fullmatch(k)]
        elif "*" in filter or "?" in filter:
            elements = [k for k in self.__ALL.keys() if fnmatch.fnmatch(k, filter)]
        else:
            elements = [filter]

        return elements

    def fill_array(
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
                raise PyAMLException(
                    f"{constructor.__name__} {array_name} : duplicate name {name} @index {len(a)}"
                ) from None
            a.append(m)
        ARR[array_name] = constructor(array_name, a)

    def __add(self, array, element: Element):
        if element.get_name() in self.__ALL:  # Ensure name unicity
            raise PyAMLException(
                f"Duplicate element {element.__class__.__name__} name {{element.get_name()}}"
            ) from None
        array[element.get_name()] = element
        self.__ALL[element.get_name()] = element

    def __get(self, what, name, array) -> Element:
        if name not in array:
            raise PyAMLException(f"{what} {name} not defined")
        return array[name]

    # Generic elements
    def fill_element_array(self, arrayName: str, elementNames: list[str]):
        self.fill_array(
            arrayName,
            elementNames,
            self.get_element,
            ElementArray,
            self.__ELEMENT_ARRAYS,
        )

    def get_element(self, name: str) -> Element:
        return self.__get("Element", name, self.__ALL)

    def get_elements(self, name: str) -> ElementArray:
        return self.__get("Element array", name, self.__ELEMENT_ARRAYS)

    def get_all_elements(self) -> list[Element]:
        return [value for key, value in self.__ALL.items()]

    # Magnets

    def fill_magnet_array(self, arrayName: str, elementNames: list[str]):
        self.fill_array(arrayName, elementNames, self.get_magnet, MagnetArray, self.__MAGNET_ARRAYS)

    def get_magnet(self, name: str) -> Magnet:
        return self.__get("Magnet", name, self.__MAGNETS)

    def add_magnet(self, m: Magnet):
        self.__add(self.__MAGNETS, m)

    def get_magnets(self, name: str) -> MagnetArray:
        return self.__get("Magnet array", name, self.__MAGNET_ARRAYS)

    def get_all_magnets(self) -> list[Magnet]:
        return [value for key, value in self.__MAGNETS.items()]

    # Combined Function Magnets

    def fill_cfm_magnet_array(self, arrayName: str, elementNames: list[str]):
        self.fill_array(
            arrayName,
            elementNames,
            self.get_cfm_magnet,
            CombinedFunctionMagnetArray,
            self.__CFM_MAGNET_ARRAYS,
        )

    def get_cfm_magnet(self, name: str) -> Magnet:
        return self.__get("CombinedFunctionMagnet", name, self.__CFM_MAGNETS)

    def add_cfm_magnet(self, m: Magnet):
        self.__add(self.__CFM_MAGNETS, m)

    def get_cfm_magnets(self, name: str) -> CombinedFunctionMagnetArray:
        return self.__get("CombinedFunctionMagnet array", name, self.__CFM_MAGNET_ARRAYS)

    def get_all_cfm_magnets(self) -> list[CombinedFunctionMagnet]:
        return [value for key, value in self.__CFM_MAGNETS.items()]

    # Serialized magnets

    def fill_serialized_magnet_array(self, arrayName: str, elementNames: list[str]):
        self.fill_array(
            arrayName,
            elementNames,
            self.get_serialized_magnet,
            SerializedMagnetsArray,
            self.__SERIALIZED_MAGNETS_ARRAYS,
        )

    def get_serialized_magnet(self, name: str) -> Magnet:
        return self.__get("SerializedMagnets", name, self.__SERIALIZED_MAGNETS)

    def add_serialized_magnet(self, m: Magnet):
        self.__add(self.__SERIALIZED_MAGNETS, m)

    def get_serialized_magnets(self, name: str) -> SerializedMagnetsArray:
        return self.__get("SerializedMagnets array", name, self.__SERIALIZED_MAGNETS_ARRAYS)

    def get_all_serialized_magnets(self) -> list[SerializedMagnets]:
        return [value for key, value in self.__SERIALIZED_MAGNETS.items()]

    # BPMs

    def fill_bpm_array(self, arrayName: str, elementNames: list[str]):
        self.fill_array(
            arrayName,
            elementNames,
            self.get_bpm,
            BPMArray,
            self.__BPM_ARRAYS,
        )

    def get_bpm(self, name: str) -> BPM:
        return self.__get("BPM", name, self.__BPMS)

    def add_bpm(self, bpm: BPM):
        self.__add(self.__BPMS, bpm)

    def get_bpms(self, name: str) -> BPMArray:
        return self.__get("BPM array", name, self.__BPM_ARRAYS)

    def get_all_bpms(self) -> list[BPM]:
        return [value for key, value in self.__BPMS.items()]

    # RF

    def get_rf_plant(self, name: str) -> RFPlant:
        return self.__get("RFPlant", name, self.__RFPLANT)

    def add_rf_plant(self, rf: RFPlant):
        self.__add(self.__RFPLANT, rf)

    def add_rf_transnmitter(self, rf: RFTransmitter):
        self.__add(self.__RFTRANSMITTER, rf)

    def get_rf_trasnmitter(self, name: str) -> RFTransmitter:
        return self.__get("RFTransmitter", name, self.__RFTRANSMITTER)

    # Tune monitor

    def get_betatron_tune_monitor(self, name: str) -> BetatronTuneMonitor:
        return self.__get("Diagnostic", name, self.__DIAG)

    def add_betatron_tune_monitor(self, tune_monitor: Element):
        self.__add(self.__DIAG, tune_monitor)

    # Tuning/Measurement tools

    def add_tool(self, tool: Element):
        self.__add(self.__TUNING_TOOLS, tool)

    # ---- Chromaticity -------------------------------------------------

    def get_chromaticity_monitor(self, name: str) -> ChomaticityMonitor:
        obj = self.__get("Chomaticity monitor", name, self.__TUNING_TOOLS)
        return obj

    def get_chromaticity_tuning(self, name: str) -> "Chromaticity":
        return self.__get("Chromaticity tool", name, self.__TUNING_TOOLS)

    def get_crm_tuning(self, name: str) -> "ChromaticityResponseMatrix":
        return self.__get("ChromaticityResponseMatrix tool", name, self.__TUNING_TOOLS)

    @property
    def chromaticity(self) -> "Chromaticity":
        return self.get_chromaticity_tuning("DEFAULT_CHROMATICITY_CORRECTION")

    @property
    def crm(self) -> "ChromaticityResponseMatrix":
        return self.get_crm_tuning("DEFAULT_CHROMATICITY_RESPONSE_MATRIX")

    # ---- Tune ---------------------------------------------------------

    def get_tune_tuning(self, name: str) -> "Tune":
        return self.__get("Tune tuning tool", name, self.__TUNING_TOOLS)

    @property
    def tune(self) -> "Tune":
        return self.get_tune_tuning("DEFAULT_TUNE_CORRECTION")

    def get_trm_tuning(self, name: str) -> "TuneResponseMatrix":
        return self.__get("TuneResponseMatrix tool", name, self.__TUNING_TOOLS)

    @property
    def trm(self) -> "TuneResponseMatrix":
        return self.get_trm_tuning("DEFAULT_TUNE_RESPONSE_MATRIX")

    # ---- Orbit --------------------------------------------------------

    def get_orbit_tuning(self, name: str) -> "Orbit":
        return self.__get("Orbit tuning tool", name, self.__TUNING_TOOLS)

    @property
    def orbit(self) -> "Orbit":
        return self.get_orbit_tuning("DEFAULT_ORBIT_CORRECTION")

    def get_orm_tuning(self, name: str) -> "OrbitResponseMatrix":
        return self.__get("OrbitResponseMatrix tool", name, self.__TUNING_TOOLS)

    @property
    def orm(self) -> "OrbitResponseMatrix":
        return self.get_orm_tuning("DEFAULT_ORBIT_RESPONSE_MATRIX")

    # ---- Dispersive orbit --------------------------------------------

    def get_dispersion_tuning(self, name: str) -> "Dispersion":
        return self.__get("Dispersion tool", name, self.__TUNING_TOOLS)

    @property
    def dispersion(self) -> "Dispersion":
        return self.get_dispersion_tuning("DEFAULT_DISPERSION")

    def _get_array(self, name: str):
        """
        Generic array resolver used by YellowPages.

        The method returns the array object referenced by 'name', regardless of its
        concrete type.
        """
        if name in self.__BPM_ARRAYS:
            return self.__BPM_ARRAYS[name]
        if name in self.__MAGNET_ARRAYS:
            return self.__MAGNET_ARRAYS[name]
        if name in self.__CFM_MAGNET_ARRAYS:
            return self.__CFM_MAGNET_ARRAYS[name]
        if name in self.__SERIALIZED_MAGNETS_ARRAYS:
            return self.__SERIALIZED_MAGNETS_ARRAYS[name]
        if name in self.__ELEMENT_ARRAYS:
            return self.__ELEMENT_ARRAYS[name]

        raise PyAMLException(f"Array {name} not defined")

    def _get_tool(self, name: str):
        """
        Generic tuning tool resolver used by YellowPages.
        """
        if name not in self.__TUNING_TOOLS:
            raise PyAMLException(f"Tool {name} not defined")
        return self.__TUNING_TOOLS[name]

    def _get_diagnostic(self, name: str):
        """
        Generic diagnostic resolver used by YellowPages.
        """
        if name not in self.__DIAG:
            raise PyAMLException(f"Diagnostic {name} not defined")
        return self.__DIAG[name]

    def _list_arrays(self) -> list[str]:
        """
        Return all array identifiers available in this holder.
        """
        arrays: list[str] = []
        arrays.extend(self.__BPM_ARRAYS.keys())
        arrays.extend(self.__MAGNET_ARRAYS.keys())
        arrays.extend(self.__CFM_MAGNET_ARRAYS.keys())
        arrays.extend(self.__SERIALIZED_MAGNETS_ARRAYS.keys())
        arrays.extend(self.__ELEMENT_ARRAYS.keys())
        return arrays

    def _list_tools(self) -> list[str]:
        """
        Return all tuning tool identifiers available in this holder.
        """
        return list(self.__TUNING_TOOLS.keys())

    def _list_diagnostics(self) -> list[str]:
        """
        Return all diagnostic identifiers available in this holder.
        """
        return list(self.__DIAG.keys())

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
