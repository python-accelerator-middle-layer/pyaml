from abc import ABCMeta, abstractmethod

import numpy.typing as npt
import numpy as np
from .readback_value import Value

class DeviceAccessList(metaclass=ABCMeta):
    """
    Abstract class providing access to a list of control system float variable
    """

    @abstractmethod
    def names(self) -> list[str]:
        """Return the names of the variables"""
        pass

    @abstractmethod
    def set_names(self,names:list[str]):
        """Set the names of the variables"""
        pass

    @abstractmethod
    def measure_names(self) -> list[str]:
        """Return the names of the measures"""
        pass

    @abstractmethod
    def set_measuresnames(self,names:list[str]):
        """Set the names of the variables"""
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
    def readback(self) -> npt.NDArray[Value]:
        """Return the measured variables"""
        pass

    @abstractmethod
    def unit(self) -> str:
        """Return the variable unit"""
        pass
