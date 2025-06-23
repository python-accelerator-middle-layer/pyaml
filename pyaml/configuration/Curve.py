from abc import ABCMeta, abstractmethod
from numpy import array

class Curve(metaclass=ABCMeta):
    """
    Abstract class providing access to a curve
    """
    @abstractmethod
    def get_curve(self) -> array:
        pass
