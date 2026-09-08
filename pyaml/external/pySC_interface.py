"""
Adapter between PyAML elements and pySC measurement applications.

The :class:`pySCInterface` exposes the orbit, magnet-strength, and RF-frequency
operations expected by pySC while using PyAML element-holder accessors.
"""

import time
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np

if TYPE_CHECKING:
    from ..common.holders.element_holder import ElementHolder
from ..common.exception import PyAMLException


class pySCInterface:
    """
    Provide pySC-compatible access to a PyAML accelerator mode.

    Parameters
    ----------
    element_holder : 'ElementHolder'
        Accelerator mode, control system or simulator, exposed to pySC.
    bpm_array_name : str
        Name of the BPM array used for orbit readback.
    rf_plant_name : Optional[str]
        Optional RF plant name, required for RF-related pySC operations.

    Methods
    -------
    get_orbit()
        Return horizontal and vertical orbit readings from the BPM array.
    get(name)
        Return the current strength of a named magnet.
    set(name, value)
        Set the strength of a named magnet and wait for the configured delay.
    get_rf_main_frequency()
        Return the main RF frequency from the configured RF plant.
    set_rf_main_frequency(value)
        Set the main RF frequency and wait for the configured delay.
    """

    set_wait_time: float = 0
    read_wait_time: float = 0

    def __init__(
        self,
        element_holder: "ElementHolder",
        bpm_array_name: str,
        rf_plant_name: Optional[str] = None,
    ):
        """
        Initialize a pySC adapter from a PyAML element holder.
        """
        self.element_holder = element_holder

        self.bpm_array = element_holder.bpms.get(bpm_array_name)

        self.rf_plant_name = rf_plant_name
        if rf_plant_name is not None:
            self.rf_plant = element_holder.rf.get(self.rf_plant_name)
        else:
            self.rf_plant = None

    def get_orbit(self) -> Tuple[np.array, np.array]:
        """Return horizontal and vertical orbit readings from the BPM array."""
        time.sleep(self.read_wait_time)
        positions = self.bpm_array.positions.get()
        return positions[:, 0], positions[:, 1]

    def get(self, name: str) -> float:
        """
        Return the current strength of a named magnet.

        Parameters
        ----------
        name : str
            Magnet name in the configured element holder.

        Returns
        -------
        float
            Current magnet strength.
        """
        magnet = self.element_holder.magnet.get(name=name)
        return magnet.strength.get()

    def set(self, name: str, value: float) -> None:
        """
        Set the strength of a named magnet and wait for the configured delay.

        Parameters
        ----------
        name : str
            Magnet name in the configured element holder.
        value : float
            New magnet strength.

        Returns
        -------
        None
            This method does not return a value.
        """
        magnet = self.element_holder.magnet.get(name=name)
        magnet.strength.set(value=value)  # ideally set_and_wait but not implemented
        time.sleep(self.set_wait_time)
        return

    def get_rf_main_frequency(self) -> float:
        """Return the main RF frequency from the configured RF plant."""
        if self.rf_plant is None:
            raise PyAMLException("RF plant name was not provided.")
        return self.rf_plant.frequency.get()

    def set_rf_main_frequency(self, value: float) -> None:
        """
        Set the main RF frequency and wait for the configured delay.

        Parameters
        ----------
        value : float
            New main RF frequency in hertz.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self.rf_plant is None:
            raise PyAMLException("RF plant name was not provided.")
        self.rf_plant.frequency.set(value)
        time.sleep(self.set_wait_time)
        return
