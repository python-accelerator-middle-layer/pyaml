from abc import ABCMeta, abstractmethod
from numpy import array
from pydantic import BaseModel

class Curve(BaseModel,metaclass=ABCMeta):
    """
    Abstract class providing access to a curve
    """
    @abstractmethod
    def get_curve(self) -> array:
        pass
