from ..control.abstract import ReadWriteFloatArray
from ..magnet.magnet import Magnet
import numpy as np

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
        return [m.strength.unit() for m in self.__magnets]

class RWMagnetHardware(ReadWriteFloatArray):

    def __init__(self, magnets:list[Magnet]):
        self.__magnets = magnets

    # Gets the values
    def get(self) -> np.array:
        return np.array([m.hardware.get() for m in self.__magnets])

    # Sets the values
    def set(self, value:np.array):
        for idx,m in enumerate(self.__magnets):
            m.hardware.set(value[idx])
        
    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        return [m.hardware.unit() for m in self.__magnets]

class MagnetArray(list[Magnet]):
    """
    Class that implements access to a magnet array
    """
    def __init__(self,iterable):
        super().__init__(i for i in iterable)
        self.__rwstrengths = RWMagnetStrength(iterable)
        self.__rwhardwares = RWMagnetHardware(iterable)

    @property
    def strengths(self) -> RWMagnetStrength:
        return self.__rwstrengths

    @property
    def hardwares(self) -> RWMagnetHardware:
        return self.__rwhardwares


    


    