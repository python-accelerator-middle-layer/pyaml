from ..control.abstract import ReadWriteFloatArray
from ..magnet.magnet import Magnet
import numpy as np
from ..control.deviceaccesslist import DeviceAccessList

class RWMagnetStrength(ReadWriteFloatArray):

    def __init__(self, magnets:list[Magnet]):
        self.__magnets = magnets
        self.aggregator:DeviceAccessList = None
        self.devices_nb:list[int] = None

    # Gets the values
    def get(self) -> np.array:
        if not self.aggregator:
            return np.array([m.strength.get() for m in self.__magnets])
        else:            
            allHardwareValues = self.aggregator.get() # Read all hardware setpoints
            allStrength = []
            mIdx = 0
            idx = 0
            for m in self.__magnets:
                nbDev = self.devices_nb[mIdx]
                allStrength.append( m.model.compute_strengths(allHardwareValues[idx:idx+nbDev]) )
                mIdx += 1
                idx += nbDev
            return allStrength

    # Sets the values
    def set(self, value:np.array):
        if not self.aggregator:
            for idx,m in enumerate(self.__magnets):
                m.strength.set(value[idx])
        else:
            allHardwareValues = self.aggregator.get() # Read all hardware setpoints
            newHardwareValues = []
            mIdx = 0
            idx = 0
            for m in self.__magnets: 
                # m is a single function magnet or a mapping to a 
                # combined function magnet (RWMapper)
                nbDev = self.devices_nb[mIdx]
                mStrengths = m.model.compute_strengths( allHardwareValues[idx:idx+nbDev] )
                mStrengths[m.index()] = value[mIdx]
                newHardwareValues.append( m.model.compute_hardware_values(mStrengths) )
                mIdx += 1
                idx += nbDev
            self.aggregator.set(newHardwareValues)
        
    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        return [m.strength.unit() for m in self.__magnets]

    # Set the aggregator (Control system only)
    def set_aggregator(self,agg:DeviceAccessList,devices_nb:list[int]):
        self.aggregator = agg    
        self.devices_nb = devices_nb

class RWMagnetHardware(ReadWriteFloatArray):

    def __init__(self, magnets:list[Magnet]):
        self.__magnets = magnets
        self.aggregator:DeviceAccessList = None

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

    # Set the aggregator (Control system only)
    def set_aggregator(self,agg:DeviceAccessList,devices_nb:list[int]):
        self.aggregator = agg
        self.devices_nb = devices_nb

class MagnetArray(list[Magnet]):
    """
    Class that implements access to a magnet array
    """
    def __init__(self,iterable):
        super().__init__(i for i in iterable)
        self.__rwstrengths = RWMagnetStrength(iterable)
        self.__rwhardwares = RWMagnetHardware(iterable)

    # Set the aggregator (Control system only)
    def set_aggregator(self,agg:DeviceAccessList,devices_nb:list[int]):
        self.__rwstrengths.set_aggregator(agg,devices_nb)
        self.__rwhardwares.set_aggregator(agg,devices_nb)

    @property
    def strengths(self) -> RWMagnetStrength:
        return self.__rwstrengths

    @property
    def hardwares(self) -> RWMagnetHardware:
        return self.__rwhardwares


    


    