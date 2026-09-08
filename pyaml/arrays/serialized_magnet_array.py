"""
Serialized Magnet Array module.

This module provides serialized magnet array functionality.
"""

import numpy as np

from ..common.abstract import ReadWriteFloatArray
from ..common.exception import PyAMLException
from ..magnet.serialized_magnet import SerializedMagnets
from .element_array import ElementArray

# TODO handle aggregator for serialized magnets


class RWMagnetStrengths(ReadWriteFloatArray):
    """
    Array accessor for the strengths of serialized magnet groups.

    Parameters
    ----------
    name : str
        Name of the array, used when the accessor is reported or logged.
    magnets : list[SerializedMagnets]
        Serialized magnet groups making up the array, in the order their values are read and written.

    Methods
    -------
    get()
        Return the shared strength of every serialized group.
    set(value)
        Set the shared strength of every serialized group.
    set_and_wait(value)
        Set every shared strength and wait for the readbacks to converge.
    unit()
        Return the strength unit of every serialized group.
    """

    def __init__(self, name: str, magnets: list[SerializedMagnets]):
        """
        Initialize the RWMagnetStrengths.
        """
        self.__name = name
        self.__magnets = magnets
        self.__nb = sum(m.get_nb_magnets() for m in magnets)

    # Gets the values
    def get(self) -> np.array:
        """Return the shared strength of every serialized group."""
        return np.array([m.strength.get() for m in self.__magnets])

    # Sets the values
    def set(self, value: np.array):
        """
        Set the shared strength of every serialized group.

        Parameters
        ----------
        value : np.array
            Shared strength for each serialized group, ordered like the array.
        """
        nvalue = np.ones(len(self.__magnets)) * value if isinstance(value, float) else value
        for value, m in zip(nvalue, self.__magnets, strict=True):
            m.strength.set(value)

    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value: np.array):
        """
        Set every shared strength and wait for the readbacks to converge.

        Parameters
        ----------
        value : np.array
            Shared strength for each serialized group, ordered like the array.

        Raises
        ------
        NotImplementedError
            Waiting for readback convergence is not implemented for this accessor.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        """Return the strength unit of every serialized group."""
        r = []
        for m in self.__magnets:
            r.extend(m.strength.unit())
        return r


class RWMagnetHardwares(ReadWriteFloatArray):
    """
    Array accessor for the hardware values of serialized magnet groups.

    Parameters
    ----------
    name : str
        Name of the array, used when the accessor is reported or logged.
    magnets : list[SerializedMagnets]
        Serialized magnet groups making up the array, in the order their values are read and written.

    Methods
    -------
    get()
        Return the shared hardware value of every serialized group.
    set(value)
        Set the shared hardware value of every serialized group.
    set_and_wait(value)
        Set every shared hardware value and wait for the readbacks to converge.
    unit()
        Return the hardware unit of every serialized group.
    """

    def __init__(self, name: str, magnets: list[SerializedMagnets]):
        """
        Initialize the RWMagnetHardwares.
        """
        self.__name = name
        self.__magnets = magnets
        self.__nb = sum(m.get_nb_magnets() for m in magnets)

    # Gets the values
    def get(self) -> np.array:
        """Return the shared hardware value of every serialized group."""
        return np.array([m.hardware.get() for m in self.__magnets])

    # Sets the values
    def set(self, value: np.array):
        """
        Set the shared hardware value of every serialized group.

        Parameters
        ----------
        value : np.array
            Shared hardware value for each serialized group, ordered like the array.
        """
        nvalue = np.ones(len(self.__magnets)) * value if isinstance(value, float) else value
        for value, m in zip(nvalue, self.__magnets, strict=True):
            m.hardware.set(value)

    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value: np.array):
        """
        Set every shared hardware value and wait for the readbacks to converge.

        Parameters
        ----------
        value : np.array
            Shared hardware value for each serialized group, ordered like the array.

        Raises
        ------
        NotImplementedError
            Waiting for readback convergence is not implemented for this accessor.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        """Return the hardware unit of every serialized group."""
        r = []
        for m in self.__magnets:
            r.extend(m.hardware.unit())
        return r


class SerializedMagnetsArray(ElementArray):
    """
    Class that implements access to a serialized magnets array

    Parameters
    ----------
    arrayName : str
        Array name
    magnets : list[SerializedMagnets]
        Magnet list, all elements must be attached to the same instance of
        either a Simulator or a ControlSystem.
    use_aggregator : bool
        Use aggregator to increase performance by using parallel
        access to underlying devices.

    Attributes
    ----------
    strengths
        Give access to strength of each magnet of this array
    hardwares
        Give access to hardware value of each magnet of this array
    """

    def __init__(
        self,
        arrayName: str,
        magnets: list[SerializedMagnets],
        use_aggregator=False,
    ):
        """
        Initialize the SerializedMagnetsArray.
        """
        super().__init__(arrayName, magnets, use_aggregator)

        self.__rwstrengths = RWMagnetStrengths(arrayName, magnets)
        self.__rwhardwares = RWMagnetHardwares(arrayName, magnets)

        if use_aggregator:
            raise (PyAMLException("Aggregator not implemented for SerializedMagnetsArray"))

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
