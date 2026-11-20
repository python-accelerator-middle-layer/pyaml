"""
Abstract read/write interfaces for scalar and array values.

The interfaces define the small protocol used by PyAML runtime elements to
read values, write setpoints, report units, and map scalar channels onto
array-backed data.
"""

from abc import ABCMeta, abstractmethod

from numpy import array, double

from .units import AcceptsQuantity

# Float ----------------------------------------------------------------


class ReadFloatScalar(AcceptsQuantity, metaclass=ABCMeta):
    """
    Define read-only access to one floating-point value.

    Methods
    -------
    get(quantity=False)
        Return the current scalar value.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    @abstractmethod
    def get(self) -> double:
        """
        Return the current scalar value.

        ``get(quantity=True)`` returns a :class:`pint.Quantity` in ``unit()``
        (see :class:`~pyaml.common.units.AcceptsQuantity`).

        Returns
        -------
        float
            Current value.
        """
        pass

    @abstractmethod
    def unit(self) -> str:
        """
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().

        A :class:`pint.Quantity` passed to ``set()`` is converted to this unit.
        Unit strings use the pyAML canonical format (see :mod:`pyaml.common.units`).

        Returns
        -------
        str
            Unit label.
        """
        pass

    def control_system_unit(self) -> str | None:
        """
        Return the control-system unit for this quantity.

        Same as ``unit()`` by default, for values that no control-system
        device holds (simulator, computed values). Unit strings use the pyAML
        canonical format (see :mod:`pyaml.common.units`).

        Returns
        -------
        str or None
            Unit label.
        """
        return self.unit()


class ReadWriteFloatScalar(ReadFloatScalar):
    """
    Define read/write access to one floating-point value.

    Methods
    -------
    set(value)
        Write a scalar setpoint.
    set_and_wait(value)
        Write a setpoint and wait for readback confirmation.
    """

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


class ReadFloatArray(AcceptsQuantity, metaclass=ABCMeta):
    """
    Define read-only access to an array of floating-point values.

    Methods
    -------
    get(quantity=False)
        Return the current values as an array.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    @abstractmethod
    def get(self) -> array:
        """
        Return the current values as an array.

        ``get(quantity=True)`` returns a :class:`pint.Quantity` in ``unit()``
        (see :class:`~pyaml.common.units.AcceptsQuantity`).
        """
        pass

    @abstractmethod
    def unit(self) -> str | list[str]:
        """
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().

        A single unit when all values share it, one unit per value (shaped
        like ``get()``) only when they differ. Unit strings use the pyAML canonical format
        (see :mod:`pyaml.common.units`).

        Returns
        -------
        str or list of str
            Unit label(s).
        """
        pass

    def control_system_unit(self) -> str | list[str | None] | None:
        """
        Return the control-system unit for this quantity.

        A single unit when all devices share it, one unit per value (shaped
        like ``get()``) only when they differ. Same as ``unit()`` by default,
        for values that no control-system device holds (simulator, computed
        values). Unit strings use the pyAML canonical format
        (see :mod:`pyaml.common.units`).

        Returns
        -------
        str or list of str or None
            Unit label(s).
        """
        return self.unit()


class ReadWriteFloatArray(ReadFloatScalar):
    """
    Define read/write access to an array of floating-point values.

    Methods
    -------
    set(value)
        Write array values in the interface's defined order.
    set_and_wait(value)
        Write array values and wait for readback confirmation.
    """

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

    Methods
    -------
    get()
        Get the value at the mapped index.
    set(value)
        Set the value at the mapped index.
    set_and_wait(value)
        Set the value and wait for it to reach the setpoint.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    index()
        Get the mapped array index.
    """

    def __init__(self, bind, idx: int):
        """
        Initialize the RWMapper.
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
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().

        Returns
        -------
        str
            Unit label of the value at the mapped index.
        """
        unit = self.bind.unit()
        return unit if isinstance(unit, str) or unit is None else unit[self.idx]

    def control_system_unit(self) -> str | None:
        """
        Return the control-system unit for this quantity.

        Returns
        -------
        str or None
            Unit label of the device at the mapped index.
        """
        unit = self.bind.control_system_unit()
        return unit if isinstance(unit, str) or unit is None else unit[self.idx]

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
