from abc import ABCMeta, abstractmethod

import numpy as np
import numpy.typing as npt

from .deviceaccess import DeviceAccess
from .readback_value import Value


class DeviceAccessList(list[DeviceAccess], metaclass=ABCMeta):
    """
    Abstract class providing access to a list of control system float variable
    """

    @abstractmethod
    def add_devices(self, devices: DeviceAccess | list[DeviceAccess]):
        """Add a DeviceAccess to this list"""
        pass

    @abstractmethod
    def get_devices(self) -> DeviceAccess | list[DeviceAccess]:
        """Get the DeviceAccess list"""
        pass

    @abstractmethod
    def set(self, value: npt.NDArray[np.float64]):
        """Write a list of control system device variable
        (i.e. a power supply currents)"""
        pass

    @abstractmethod
    def set_and_wait(self, value: npt.NDArray[np.float64]):
        """Write a list control system device variable (i.e. a power supply currents)"""
        pass

    @abstractmethod
    def get(self) -> npt.NDArray[np.float64]:
        """Return a list of setpoints of control system device variables"""
        pass

    @abstractmethod
    def readback(self) -> np.array:
        """Return the measured variables"""
        pass

    @abstractmethod
    def unit(self) -> str:
        """Return the variable unit"""
        pass

    @abstractmethod
    def get_range(self) -> list[float]:
        """
        Get the valid range for the device variables.

        Returns
        -------
        list[float]
            List containing [min, max] values
        """
        pass

    @abstractmethod
    def check_device_availability(self) -> bool:
        """
        Check if all devices in the list are available and accessible.

        Returns
        -------
        bool
            True if all devices are available, False otherwise
        """
        pass
