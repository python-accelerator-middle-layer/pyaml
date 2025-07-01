from abc import ABCMeta, abstractmethod
from pydantic import BaseModel

class DeviceAccess(BaseModel,metaclass=ABCMeta):
    """
    Abstract class providing strength to coil current conversion and access to underlying power supplies
    """

    # Sets the value
    @abstractmethod
    def set(self, value: float):
        pass

    # Get the setpoint
    @abstractmethod
    def get(self) -> float:
        pass

    # Get the measured value
    @abstractmethod
    def readback() -> float:
        pass

    # Get the unit
    @abstractmethod
    def unit(self) -> str:
        pass
