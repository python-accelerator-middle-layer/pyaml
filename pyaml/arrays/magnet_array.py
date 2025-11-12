from ..common.abstract import ReadWriteFloatArray
from ..magnet.magnet import Magnet
from ..common.abstract_aggregator import ScalarAggregator
from .element_array import ElementArray
import numpy as np

class RWMagnetStrength(ReadWriteFloatArray):

    def __init__(self, name:str, magnets:list[Magnet]):
        self.__name = name
        self.__magnets = magnets
        self.__nb = len(self.__magnets)
        self.__aggregator:ScalarAggregator = None

    # Gets the values
    def get(self) -> np.array:
        if not self.__aggregator:
            return np.array([m.strength.get() for m in self.__magnets])
        else:
            return self.__aggregator.get()

    # Sets the values
    def set(self, value:np.array):
        nvalue = np.ones(self.__nb) * value if isinstance(value,float) else value        
        if not self.__aggregator:
            for idx,m in enumerate(self.__magnets):
                m.strength.set(nvalue[idx])
        else:
            self.__aggregator.set(nvalue)
        
    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        return [m.strength.unit() for m in self.__magnets]

    # Set the aggregator (Control system only)
    def set_aggregator(self,agg:ScalarAggregator):
        self.__aggregator = agg

class RWMagnetHardware(ReadWriteFloatArray):

    def __init__(self, name:str, magnets:list[Magnet]):
        self.__name = name
        self.__magnets = magnets
        self.__nb = len(self.__magnets)
        self.__aggregator:ScalarAggregator = None

    # Gets the values
    def get(self) -> np.array:
        if not self.__aggregator:
            return np.array([m.hardware.get() for m in self.__magnets])
        else:
            return self.__aggregator.get()

    # Sets the values
    def set(self, value:np.array):
        nvalue = np.ones(self.__nb) * value if isinstance(value,float) else value        
        if not self.__aggregator:
            for idx,m in enumerate(self.__magnets):
                m.hardware.set(value[idx])
        else:
            self.__aggregator.set(value)
        
    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        return [m.hardware.unit() for m in self.__magnets]

    # Set the aggregator
    def set_aggregator(self,agg:ScalarAggregator):
        self.__aggregator = agg

class MagnetArray(ElementArray):
    """
    Class that implements access to a magnet array
    """

    def __init__(self,arrayName:str,magnets:list[Magnet],use_aggregator = True):
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
        
        self.__rwstrengths = RWMagnetStrength(arrayName,magnets)
        self.__rwhardwares = RWMagnetHardware(arrayName,magnets)

        if use_aggregator:
            aggs = self.get_peer().create_magnet_strength_aggregator(magnets)
            aggh = self.get_peer().create_magnet_harddware_aggregator(magnets)
            self.__rwstrengths.set_aggregator(aggs)
            self.__rwhardwares.set_aggregator(aggh)

    @property        
    def strengths(self) -> RWMagnetStrength:
        """
        Give access to strength of each magnet of this array
        """
        return self.__rwstrengths

    @property
    def hardwares(self) -> RWMagnetHardware:
        """
        Give access to hardware value of each magnet of this array
        """
        return self.__rwhardwares


    


    