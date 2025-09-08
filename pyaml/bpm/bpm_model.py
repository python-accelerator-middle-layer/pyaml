from abc import ABCMeta, abstractmethod
import numpy as np
from numpy.typing import NDArray

class BPMModel(metaclass=ABCMeta):
    """
    Abstract class providing interface to accessing BPM positions, offsets,
    tilts.
    """
    @abstractmethod
    def read_hardware_positions(self) -> NDArray[np.float64]:
        """
        Read horizontal and vertical positions from a BPM.
        Returns
        -------
        NDArray[np.float64]
            Array of shape (2,) containing the horizontal and vertical
            positions
        """
        pass
    
    @abstractmethod
    def read_hardware_tilt_value(self) -> float:
        """
        Read the tilt value from a BPM.
        Returns
        -------
        float
            The tilt value of the BPM
        """
        pass

    @abstractmethod
    def read_hardware_offset_values(self) -> NDArray[np.float64]:
        """
        Read the offset values from a BPM.
        Returns
        -------
        NDArray[np.float64]
            Array of shape (2,) containing the horizontal and vertical
            offsets
        """
        pass

    @abstractmethod
    def set_hardware_tilt_value(self, tilt: float):
        """
        Set the tilt value of a BPM.
        Parameters
        ----------
        tilt : float
            The tilt value to set for the BPM
        Returns
        -------
        None
        """
        pass

    @abstractmethod
    def set_hardware_offset_values(self, offset_values: NDArray[np.float64]):
        """
        Set the offset values of a BPM
        Parameters
        ----------
        offset_values : NDArray[np.float64]
            Array of shape (2,) containing the horizontal and vertical
            offsets to set for the BPM
        """
        pass

    @abstractmethod
    def get_hardware_angle_unit(self) -> str:
        """
        Get the hardware unit for BPM readings.
        Returns
        -------
        str
            The unit of measurement for BPM hardware values.
        """
        pass
    
    @abstractmethod
    def get_hardware_position_units(self) -> list[str]:
        """
        Get the hardware units for BPM positions and offsets.
        Returns
        -------
        list[str]
            List of units for horizontal and vertical positions and offsets.
        """
        pass

