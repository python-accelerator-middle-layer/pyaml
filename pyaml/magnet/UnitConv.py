from abc import ABCMeta, abstractmethod
import numpy as np

class UnitConv(metaclass=ABCMeta):
    """
    Abstract class providing strength to coil current conversion
    """
    # Get coil current(s) from magnet strength(s)
    @abstractmethod
    def get_currents(self,strengths:np.array) -> np.array:
        pass

    # Get magnet strength(s) from coil current(s)
    @abstractmethod
    def get_strengths(self,currents:np.array) -> np.array:
        pass

    # Set magnet rigidity
    @abstractmethod
    def set_magnet_rigidity(self,brho:np.double):
        pass
