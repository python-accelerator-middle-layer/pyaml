from ..common.abstract import ReadWriteFloatArray
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from .element_array import ElementArray
from ..common.exception import PyAMLException
import numpy as np

#TODO handle aggregator for CFM

class RWMagnetStrengths(ReadWriteFloatArray):

    def __init__(self, name:str, magnets:list[CombinedFunctionMagnet]):
        self.__name = name
        self.__magnets = magnets
        self.__nb = sum(m.nb_multipole() for m in magnets)

    # Gets the values
    def get(self) -> np.array:
        r = np.zeros(self.__nb)
        idx = 0
        for m in self.__magnets:
            r[idx:idx+m.nb_multipole()] = m.strengths.get()
            idx+=m.nb_multipole()
        return r

    # Sets the values
    def set(self, value:np.array):
        nvalue = np.ones(self.__nb) * value if isinstance(value,float) else value        
        idx = 0
        for m in self.__magnets:
            m.strengths.set(nvalue[idx:idx+m.nb_multipole()])
            idx+=m.nb_multipole()

    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        r = []
        for m in self.__magnets:
            r.extend(m.strengths.unit())
        return r

class RWMagnetHardwares(ReadWriteFloatArray):

    def __init__(self, name:str, magnets:list[CombinedFunctionMagnet]):
        self.__name = name
        self.__magnets = magnets
        self.__nb = sum(m.nb_multipole() for m in magnets)

    # Gets the values
    def get(self) -> np.array:
        r = np.zeros(self.__nb)
        idx = 0
        for m in self.__magnets:
            r[idx:idx+m.nb_multipole()] = m.hardwares.get()
            idx+=m.nb_multipole()
        return r

    # Sets the values
    def set(self, value:np.array):
        nvalue = np.ones(self.__nb) * value if isinstance(value,float) else value
        idx = 0
        for m in self.__magnets:
            m.hardwares.set(nvalue[idx:idx+m.nb_multipole()])
            idx+=m.nb_multipole()
        
    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        r = []
        for m in self.__magnets:
            r.extend(m.hardwares.unit())
        return r


class CombinedFunctionMagnetArray(ElementArray):
    """
    Class that implements access to a magnet array
    """

    def __init__(self,arrayName:str,magnets:list[CombinedFunctionMagnet],use_aggregator = False):
        """
        Construct a magnet array

        Parameters
        ----------
        arrayName : str
            Array name
        magnets: list[Magnet]
            Magnet list, all elements must be attached to the same instance of 
            either a Simulator or a ControlSystem.
        use_aggregator : bool
            Use aggregator to increase performance by using paralell access to underlying devices.
        """
        super().__init__(arrayName,magnets,use_aggregator)
        
        self.__rwstrengths = RWMagnetStrengths(arrayName,magnets)
        self.__rwhardwares = RWMagnetHardwares(arrayName,magnets)

        if use_aggregator:
            raise(PyAMLException("Aggregator not implemented for CombinedFunctionMagnetArray"))

    @property        
    def strengths(self) -> RWMagnetStrengths:
        """
        Give access to strength of each magnet of this array
        """
        return self.__rwstrengths

    @property
    def hardwares(self) -> RWMagnetHardwares:
        """
        Give access to hardware value of each magnet of this array
        """
        return self.__rwhardwares


    


    