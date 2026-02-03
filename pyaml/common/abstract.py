from abc import ABCMeta, abstractmethod

from numpy import array, double

# Float ----------------------------------------------------------------


class ReadFloatScalar(metaclass=ABCMeta):
    """
    Abstract class providing read access to a scalar double
    """

    @abstractmethod
    def get(self) -> double:
        """Get the value"""
        pass

    @abstractmethod
    def unit(self) -> str:
        """Get the unit of the value"""
        pass


class ReadWriteFloatScalar(ReadFloatScalar):
    """
    Abstract class providing read write access to a scalar double
    """

    @abstractmethod
    def set(self, value: double):
        """Set the value"""
        pass

    # Sets the value and wait that the read value reach the setpoint
    @abstractmethod
    def set_and_wait(self, value: double):
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

    @abstractmethod
    def unit(self) -> list[str]:
        """Get the unit of the values"""
        pass


class ReadWriteFloatArray(ReadFloatScalar):
    """
    Abstract class providing read write access to a vector of double
    """

    @abstractmethod
    def set(self, value: array):
        """Set the values"""
        pass

    # Sets the value and waits that the read value reach the setpoint
    @abstractmethod
    def set_and_wait(self, value: array):
        """Set the values and wait that setpoints are reached"""
        pass


class RWMapper(ReadWriteFloatScalar):
    """
    Class mapping a scalar to an element of an array
    """

    def __init__(self, bind, idx: int):
        self.bind = bind
        self.idx = idx

    # Gets the value
    def get(self) -> float:
        """
        Get the value at the mapped index.

        Returns
        -------
        float
            Value at the mapped array index
        """
        return self.bind.get()[self.idx]

    # Sets the value
    def set(self, value: float):
        """
        Set the value at the mapped index.

        Parameters
        ----------
        value : float
            Value to set
        """
        arr = self.bind.get()
        arr[self.idx] = value
        self.bind.set(arr)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        """
        Set the value and wait for it to reach the setpoint.

        Parameters
        ----------
        value : float
            Target value to set and wait for

        Raises
        ------
        NotImplementedError
            This method is not yet implemented
        """
        raise NotImplementedError("Not implemented yet.")

    # Return the unit
    def unit(self) -> str:
        """
        Get the unit for the value.

        Returns
        -------
        str
            Unit string for the value at the mapped index
        """
        return self.bind.unit()[self.idx]

    # Return the mapped index
    def index(self) -> int:
        """
        Get the mapped array index.

        Returns
        -------
        int
            The index in the array that this scalar maps to
        """
        return self.idx
