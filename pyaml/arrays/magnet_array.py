from ..control.abstract import ReadWriteFloatArray
from ..magnet.magnet import Magnet
import numpy as np

#TODO: Implement magnet_array.RWMagnetCurrent

class RWMagnetStrength(ReadWriteFloatArray):

    def __init__(self, magnets:list[Magnet]):
        self.__magnets = magnets

    # Gets the values
    def get(self) -> np.array:
        return np.array([m.strength.get() for m in self.__magnets])

    # Sets the values
    def set(self, value:np.array):
        for idx,m in enumerate(self.__magnets):
            m.strength.set(value[idx])
        
    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        [m.strength.unit() for m in self.__magnets]

class MagnetArray(object):
    """
    Class that implements access to a magnet arrays
    """
    def __init__(self,magnets:list[Magnet]):
        self.__rwstrengths = RWMagnetStrength(magnets)

    @property
    def strengths(self) -> RWMagnetStrength:
        return self.__rwstrengths



    


    