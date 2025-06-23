from abc import ABCMeta, abstractmethod
from numpy import array

class UnitConv(metaclass=ABCMeta):
    """
    Abstract class providing strength to coil current conversion
    """
    # Get coil current(s) from magnet strength(s)
    @abstractmethod
    def get_currents(self,strengths:array) -> array:
        pass

    # Get magnet strength(s) from coil current(s)
    @abstractmethod
    def get_strengths(self,strengths:array) -> array:
        pass
