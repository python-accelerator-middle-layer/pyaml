from abc import ABCMeta, abstractmethod
import numpy as np
from numpy.typing import NDArray
from ..control.deviceaccess import DeviceAccess

class BPMModel(metaclass=ABCMeta):
    """
    Abstract class providing interface to accessing BPM positions, offsets,
    tilts.
    """
    @abstractmethod
    def read_position(self) -> NDArray[np.float64]:
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
    def read_tilt(self) -> float:
        """
        Read the tilt value from a BPM.
        Returns
        -------
        float
            The tilt value of the BPM
        """
        pass

    @abstractmethod
    def read_offset(self) -> NDArray:
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
    def set_tilt(self, tilt: float):
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
    def set_offset(self, offset: NDArray[np.float64]):
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
    def get_pos_devices(self) -> list[DeviceAccess]:
        """
        Get device handles used for position reading
        
        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        pass

    @abstractmethod
    def get_tilt_device(self) -> DeviceAccess:
        """
        Get device handle used for tilt access
        
        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        pass

    @abstractmethod
    def get_offset_devices(self) -> list[DeviceAccess]:
        """
        Get device handles used for offset access
        
        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        pass
