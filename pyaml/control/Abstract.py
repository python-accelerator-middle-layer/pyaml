from numpy import double
from abc import ABCMeta, abstractmethod
from numpy import array

class ReadFloatScalar(metaclass=ABCMeta):
    """
    Abstract class providing read access to a scalar double
    """
    # Gets the value
    @abstractmethod
    def get(self) -> double:
        pass
    
class ReadWriteFloatScalar(ReadFloatScalar):
    """
    Abstract class providing read write access to a scalar double
    """
    # Sets the value
    @abstractmethod
    def set(self, value:double):
        pass
        
    # Sets the value and wait that the read value reach the setpoint
    @abstractmethod
    def set_and_wait(self, value:double):
        pass


class ReadFloatArray(metaclass=ABCMeta):
    """
    Abstract class providing read access to a vector of float
    """
    # Gets the value
    @abstractmethod
    def get(self) -> array:
        pass

class ReadWriteFloatArray(ReadFloatScalar):
    """
    Abstract class providing read write access to a vector of double
    """
    # Sets the value
    @abstractmethod
    def set(self, value:array):
        pass
        
    # Sets the value and waits that the read value reach the setpoint
    @abstractmethod
    def set_and_wait(self, value:array):
        pass
