from numpy import double
from abc import ABCMeta, abstractmethod
from numpy import array

# Float ----------------------------------------------------------------

class ReadFloatScalar(metaclass=ABCMeta):
    """
    Abstract class providing read access to a scalar double
    """

    @abstractmethod
    def get(self) -> double:
        """Get the value"""
        pass

    def unit(self) -> str:
        """Get the unit of the value"""
        pass
    
class ReadWriteFloatScalar(ReadFloatScalar):
    """
    Abstract class providing read write access to a scalar double
    """
    
    @abstractmethod
    def set(self, value:double):
        """Set the value"""
        pass
        
    # Sets the value and wait that the read value reach the setpoint
    @abstractmethod
    def set_and_wait(self, value:double):
        """Set the value and wait that setpoint is reached"""
        pass


class ReadFloatArray(metaclass=ABCMeta):
    """
    Abstract class providing read access to a vector of float
    """

    @abstractmethod
    def get(self) -> array:
        """Get the value"""
        pass

    def unit(self) -> list[str]:
        """Get the unit of the values"""
        pass

class ReadWriteFloatArray(ReadFloatScalar):
    """
    Abstract class providing read write access to a vector of double
    """
    @abstractmethod
    def set(self, value:array):
        """Set the values"""
        pass
        
    # Sets the value and waits that the read value reach the setpoint
    @abstractmethod
    def set_and_wait(self, value:array):
        """Set the values and wait that setpoints are reached"""
        pass

