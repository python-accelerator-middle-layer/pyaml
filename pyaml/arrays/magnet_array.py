from ..control.abstract import ReadWriteFloatArray
from ..magnet.magnet import Magnet
import numpy as np
from ..control.deviceaccesslist import DeviceAccessList

class RWMagnetStrength(ReadWriteFloatArray):

    def __init__(self, name:str, magnets:list[Magnet]):
        self.__magnets = magnets
        self.__name = name
        self.aggregator:DeviceAccessList = None

    # Gets the values
    def get(self) -> np.array:
        if not self.aggregator:
            return np.array([m.strength.get() for m in self.__magnets])
        else:
            allHardwareValues = self.aggregator.get() # Read all hardware setpoints
            allStrength = np.zeros(len(self.__magnets))
            mIdx = 0
            idx = 0
            for m in self.__magnets:
                nbDev = len(m.model.get_devices())
                allStrength[idx] = m.model.compute_strengths(allHardwareValues[idx:idx+nbDev])[m.strength.index()]
                mIdx += 1
                idx += nbDev
            return allStrength

    # Sets the values
    def set(self, value:np.array):
        if not self.aggregator:
            for idx,m in enumerate(self.__magnets):
                m.strength.set(value[idx])
        else:
            # TODO: if the array does not contains mappings to combined function 
            # magnets, the algorithm below can be optimized
            allHardwareValues = self.aggregator.get() # Read all hardware setpoints
            newHardwareValues = np.zeros(len(self.aggregator))
            mIdx = 0
            idx = 0
            for m in self.__magnets:
                # m is a single function magnet or a mapping to a 
                # combined function magnet (RWMapper)
                nbDev = len(m.model.get_devices())
                mStrengths = m.model.compute_strengths( allHardwareValues[idx:idx+nbDev] )
                mStrengths[m.strength.index()] = value[mIdx]
                newHardwareValues[idx:idx+nbDev] = m.model.compute_hardware_values(mStrengths)
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
    def set_aggregator(self,agg:DeviceAccessList):
        self.aggregator = agg

class RWMagnetHardware(ReadWriteFloatArray):

    def __init__(self, name:str, magnets:list[Magnet]):
        self.__name = name
        self.__magnets = magnets
        self.aggregator:DeviceAccessList = None
        self.hasHardwareMapping = True

    # Gets the values
    def get(self) -> np.array:
        if not self.aggregator:
            return np.array([m.hardware.get() for m in self.__magnets])
        else:
            if not self.hasHardwareMapping:
                raise Exception(f"Array {self.__name} contains elements that that do not support hardware units")
            else:
                return self.aggregator.get()

    # Sets the values
    def set(self, value:np.array):
        if not self.aggregator:
            for idx,m in enumerate(self.__magnets):
                m.hardware.set(value[idx])
        else:
            if not self.hasHardwareMapping:
                raise Exception(f"Array {self.__name} contains elements that that do not support hardware units")
            else:
                self.aggregator.set(value)
        
    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        return [m.hardware.unit() for m in self.__magnets]

    # Set the aggregator (Control system only)
    def set_aggregator(self,agg:DeviceAccessList):
        self.aggregator = agg
        for m in self.__magnets:
            self.hasHardwareMapping |= m.model.hasHardwareMapping()

class MagnetArray(list[Magnet]):
    """
    Class that implements access to a magnet array
    """

    def __init__(self,arrayName:str,iterable):
        """
        Construct a magnet array

        Parameters
        ----------
        iterable
            Magnet iterator
        """
        super().__init__(i for i in iterable)
        self.__name = arrayName
        self.__rwstrengths = RWMagnetStrength(arrayName,iterable)
        self.__rwhardwares = RWMagnetHardware(arrayName,iterable)

    def set_aggregator(self,agg:DeviceAccessList):
        """
        Set an aggregator for this array.
        Aggregator allow fast control system access by parallelizing 
        call to underlying hardware.

        Parameters
        ----------
        agg : DeviceAccessList
            List of device access
        """
        self.__rwstrengths.set_aggregator(agg)
        self.__rwhardwares.set_aggregator(agg)

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


    


    