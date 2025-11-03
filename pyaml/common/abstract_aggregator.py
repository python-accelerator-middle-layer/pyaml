from abc import ABCMeta, abstractmethod

import numpy.typing as npt
import numpy as np

class ScalarAggregator(metaclass=ABCMeta):
    """
    Abstract class providing access to a list of scalar variables
    """

    @abstractmethod
    def set(self, value: npt.NDArray[np.float64]):
        """Write a list of variable"""
        pass

    @abstractmethod
    def set_and_wait(self, value: npt.NDArray[np.float64]):
        """Write a list of variable and wait that setpoint are reached"""
        pass

    @abstractmethod
    def get(self) -> npt.NDArray[np.float64]:
        """Return a list variables"""
        pass

    @abstractmethod
    def readback(self) -> np.array:
        """Return  a list variables (measurements)"""
        pass

    @abstractmethod
    def unit(self) -> str:
        """Return the variables unit"""
        pass
