from abc import ABCMeta, abstractmethod

import numpy.typing as npt
import numpy as np
from .readback_value import Value
from .deviceaccess import DeviceAccess

class DeviceAccessList(list[DeviceAccess],metaclass=ABCMeta):
    """
    Abstract class providing access to a list of control system float variable
    """

    @abstractmethod
    def add_devices(self, devices:DeviceAccess | list[DeviceAccess]):
        """Add a DeviceAccess to this list"""        
        pass

    @abstractmethod
    def get_devices(self) -> DeviceAccess | list[DeviceAccess]:
        """Get the DeviceAccess list"""        
        pass

    @abstractmethod
    def set(self, value: npt.NDArray[np.float64]):
        """Write a list of control system device variable (i.e. a power supply currents)"""
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
