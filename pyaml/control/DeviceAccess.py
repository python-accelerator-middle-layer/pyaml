from abc import ABCMeta, abstractmethod
from pydantic import BaseModel

class DeviceAccess(BaseModel,metaclass=ABCMeta):
    """
    Abstract class providing access to a control system
    """

    """
    Write a control system device value (i.e. a power supply current)
    """
    @abstractmethod
    def set(self, value: float):
        pass

    """
    Return he setpoint of a control system device value
    """
    @abstractmethod
    def get(self) -> float:
        pass

    """
    Return the value measured
    """
    @abstractmethod
    def readback() -> float:
        pass

    """
    Return the value unit
    """
    @abstractmethod
    def unit(self) -> str:
        pass
