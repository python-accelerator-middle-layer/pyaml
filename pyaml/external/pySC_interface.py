from typing import Dict, List, Tuple

import numpy as np

from ..common.element_holder import ElementHolder
from ..common.exception import PyAMLException


class pySCInterface:
    def __init__(
        self,
        element_holder: ElementHolder,
        bpm_array_name: str = "BPM",
        hcorr_array_name: str = "HCorr",
        vcorr_array_name: str = "VCorr",
        rf_plant_name: str = "RF",
    ):
        self.element_holder = element_holder

        self.bpm_array = element_holder.get_bpms(bpm_array_name)

        # We could generalize to arbitrary arrays.
        # Presently, pySC only uses set_many and get_many to set corrector strengths
        # when doing orbit correction.
        # Technically we don't need to define it, because we can ask for the trims to
        # make for an orbit correction and then apply them in pyAML.
        # Only get and set are used for other measurements.
        self.hcorr_array_name = hcorr_array_name
        self.hcorr_array = element_holder.get_magnets(hcorr_array_name)
        self.hcorr_names = self.hcorr_array.names()
        self.hcorr_name_to_index = {
            name: ii for ii, name in enumerate(self.hcorr_names)
        }

        self.vcorr_array_name = vcorr_array_name
        self.vcorr_array = element_holder.get_magnets(vcorr_array_name)
        self.vcorr_names = self.vcorr_array.names()
        self.vcorr_name_to_index = {
            name: ii for ii, name in enumerate(self.vcorr_names)
        }

        self.rf_plant_name = rf_plant_name
        self.rf_plant = element_holder.get_rf_plant(self.rf_plant_name)

    def get_orbit(self) -> Tuple[np.array, np.array]:
        # we should wait here somehow according to polling rate
        positions = self.bpm_array.positions.get()
        return positions[:, 0], positions[:, 1]

    def get(self, name: str) -> float:
        magnet = self.element_holder.get_magnet(name=name)
        return magnet.strength.get()

    def set(self, name: str, value: float) -> None:
        magnet = self.element_holder.get_magnet(name=name)
        magnet.strength.set(value=value)  # ideally set_and_wait but not implemented
        return

    def get_many(self, names: List[str]) -> Dict[str, float]:
        get_hcorr = False
        get_vcorr = False
        name_to_array = {}

        # check if all names are accounted for and which strength arrays to get.
        for name in names:
            if name in self.hcorr_names:
                get_hcorr = True
                name_to_array[name] = "hcorr"
            elif name in self.vcorr_names:
                get_vcorr = True
                name_to_array[name] = "vcorr"
            else:
                raise PyAMLException(
                    f"{name} was not found in magnet arrays "
                    f"{self.hcorr_array_name} and {self.vcorr_array_name}"
                )

        # do actual get
        if get_hcorr:
            hcorr_strengths = self.hcorr_array.strengths.get()
        else:
            hcorr_strengths = []

        if get_vcorr:
            vcorr_strengths = self.vcorr_array.strengths.get()
        else:
            vcorr_strengths = []

        # prepare data to return
        data = {}
        for name in names:
            if name_to_array[name] == "hcorr":
                hcorr_index = self.hcorr_name_to_index[name]
                data[name] = hcorr_strengths[hcorr_index]
            elif name_to_array[name] == "vcorr":
                vcorr_index = self.vcorr_name_to_index[name]
                data[name] = vcorr_strengths[vcorr_index]
            else:
                raise PyAMLException("BUG: This should not happen.")

        return data

    def set_many(self, names_values: Dict[str, float]) -> None:
        set_hcorr = False
        set_vcorr = False
        name_to_array = {}

        names = list(names_values.keys())
        # check if all names are accounted for and which strength arrays to get/set.
        for name in names:
            if name in self.hcorr_names:
                set_hcorr = True
                name_to_array[name] = "hcorr"
            elif name in self.vcorr_names:
                set_vcorr = True
                name_to_array[name] = "vcorr"
            else:
                raise PyAMLException(
                    f"{name} was not found in magnet arrays "
                    f"{self.hcorr_array_name} and {self.vcorr_array_name}"
                )

        # first do get
        if set_hcorr:
            hcorr_strengths = self.hcorr_array.strengths.get()
        else:
            hcorr_strengths = []

        if set_vcorr:
            vcorr_strengths = self.vcorr_array.strengths.get()
        else:
            vcorr_strengths = []

        # change hcorr_strengths and vcorr_strengths according to names_values
        # (input data). We could check if original setpoint and new setpoint are not
        # the same to avoid redundant set.
        for name in names:
            if name_to_array[name] == "hcorr":
                hcorr_index = self.hcorr_name_to_index[name]
                hcorr_strengths[hcorr_index] = names_values[name]
            elif name_to_array[name] == "vcorr":
                vcorr_index = self.vcorr_name_to_index[name]
                vcorr_strengths[vcorr_index] = names_values[name]
            else:
                raise PyAMLException("BUG: This should not happen.")

        # TODO: we should check first if any value goes out of range before starting to
        # set anything
        # TODO: can weset everything together instead of settings the arrays one by one?

        if set_hcorr:
            self.hcorr_array.strengths.set(
                hcorr_strengths
            )  # ideally set_and_wait but not implemented
        if set_vcorr:
            self.vcorr_array.strengths.set(
                vcorr_strengths
            )  # ideally set_and_wait but not implemented

        return

    def get_rf_main_frequency(self) -> float:
        return self.rf_plant.frequency.get()

    def set_rf_main_frequency(self, value: float) -> None:
        self.rf_plant.frequency.set(value)
        return
