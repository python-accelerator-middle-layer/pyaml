from abc import ABCMeta, abstractmethod
from pydantic import BaseModel
from .readback_value import Value

class DeviceAccess(BaseModel,metaclass=ABCMeta):
    """
    Abstract class providing access to a control system float variable
    """

    @abstractmethod
    def name(self) -> str:
        """Return the name of the variable"""
        pass

    @abstractmethod
    def measure_name(self) -> str:
        """Return the name of the measure"""
        pass

    @abstractmethod
    def set(self, value: float):
        """Write a control system device variable (i.e. a power supply current)"""
        pass

    @abstractmethod
    def get(self) -> float:
        """Return the setpoint of a control system device variable"""
        pass

    @abstractmethod
    def readback(self) -> Value:
        """Return the measured variable"""
        pass

    @abstractmethod
    def unit(self) -> str:
        """Return the variable unit"""
        pass
