from abc import ABCMeta, abstractmethod
from pydantic import BaseModel

class DeviceAccess(BaseModel,metaclass=ABCMeta):
    """
    Abstract class providing access to a control system float value
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
        """Write a control system device value (i.e. a power supply current)"""
        pass

    @abstractmethod
    def get(self) -> float:
        """Return the setpoint of a control system device value"""
        pass

    @abstractmethod
    def readback() -> float:
        """Return the measured value"""
        pass

    @abstractmethod
    def unit(self) -> str:
        """Return the value unit"""
        pass
