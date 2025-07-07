from abc import ABCMeta, abstractmethod
from pydantic import BaseModel

class ControlSystem(BaseModel,metaclass=ABCMeta):
    """
    Abstract class providing access to a control system float variable
    """

    @abstractmethod
    def init_cs(self):
        """Initialize control system"""
        pass

    @abstractmethod
    def name(self) -> str:
        """Return control system name (i.e. live)"""
        pass
