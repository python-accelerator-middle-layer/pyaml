from typing import TYPE_CHECKING, Tuple, Optional

import numpy as np

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder
from ..common.exception import PyAMLException


class pySCInterface:
    def __init__(
        self,
        element_holder: "ElementHolder",
        bpm_array_name: str,
        rf_plant_name: Optional[str] = None,
    ):
        self.element_holder = element_holder

        self.bpm_array = element_holder.get_bpms(bpm_array_name)

        self.rf_plant_name = rf_plant_name
        if rf_plant_name is not None:
            self.rf_plant = element_holder.get_rf_plant(self.rf_plant_name)
        else:
            self.rf_plant = None

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

    def get_rf_main_frequency(self) -> float:
        if self.rf_plant is None:
            raise PyAMLException("RF plant name was not provided.")
        return self.rf_plant.frequency.get()

    def set_rf_main_frequency(self, value: float) -> None:
        if self.rf_plant is None:
            raise PyAMLException("RF plant name was not provided.")
        self.rf_plant.frequency.set(value)
        return
