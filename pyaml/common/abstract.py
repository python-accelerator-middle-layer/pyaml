"""
Abstract read/write interfaces for scalar and array values.

The interfaces define the small protocol used by PyAML runtime elements to
read values, write setpoints, report units, and map scalar channels onto
array-backed data.
"""

from abc import ABCMeta, abstractmethod

from numpy import array, double

# Float ----------------------------------------------------------------


class ReadFloatScalar(metaclass=ABCMeta):
    """Define read-only access to one floating-point value."""

    @abstractmethod
    def get(self) -> double:
        """
        Return the current scalar value.

        Returns
        -------
        float
            Current value.
        """
        pass

    @abstractmethod
    def unit(self) -> str:
        """
        Return the physical unit of the scalar value.

        Returns
        -------
        str
            Unit label.
        """
        pass


class ReadWriteFloatScalar(ReadFloatScalar):
    """Define read/write access to one floating-point value."""

    @abstractmethod
    def set(self, value: double):
        """
        Write a scalar setpoint.

        Parameters
        ----------
        value : float
            Value to write.
        """
        pass

    # Sets the value and wait that the read value reach the setpoint
    @abstractmethod
    def set_and_wait(self, value: double):
        """
        Write a setpoint and wait for readback confirmation.

        Parameters
        ----------
        value : float
            Target value.
        """
        pass


class ReadFloatArray(metaclass=ABCMeta):
    """Define read-only access to an array of floating-point values."""

    @abstractmethod
    def get(self) -> array:
        """Return the current values as an array."""
        pass

    @abstractmethod
    def unit(self) -> list[str]:
        """Return the units associated with the array values."""
        pass


class ReadWriteFloatArray(ReadFloatScalar):
    """Define read/write access to an array of floating-point values."""

    @abstractmethod
    def set(self, value: array):
        """
        Write array values in the interface's defined order.

        Parameters
        ----------
        value : numpy.ndarray
            Values to write.
        """
        pass

    # Sets the value and waits that the read value reach the setpoint
    @abstractmethod
    def set_and_wait(self, value: array):
        """
        Write array values and wait for readback confirmation.

        Parameters
        ----------
        value : numpy.ndarray
            Target values.
        """
        pass


class RWMapper(ReadWriteFloatScalar):
    """
    Expose one array element through a scalar read/write interface.

    Parameters
    ----------
    bind : ReadWriteFloatArray
        Array interface containing the mapped value.
    idx : int
        Zero-based index of the mapped element.
    """

    def __init__(self, bind, idx: int):
        """
        Initialize the RWMapper.

        Parameters
        ----------
        bind : object
            Array interface containing the mapped value.
        idx : int
            Zero-based index of the mapped element.
        """
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
