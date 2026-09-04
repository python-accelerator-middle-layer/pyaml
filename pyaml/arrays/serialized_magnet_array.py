"""Serialized Magnet Array module.

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
    RWMagnetStrengths configuration or runtime object.

    Parameters
    ----------
    name : str
        Input value for this operation.
    magnets : list[SerializedMagnets]
        Input value for this operation.
    """

    def __init__(self, name: str, magnets: list[SerializedMagnets]):
        """
        Initialize the RWMagnetStrengths.

        Parameters
        ----------
        name : str
            Input value for this operation.
        magnets : list[SerializedMagnets]
            Input value for this operation.
        """
        self.__name = name
        self.__magnets = magnets
        self.__nb = sum(m.get_nb_magnets() for m in magnets)

    # Gets the values
    def get(self) -> np.array:
        """Execute get."""
        return np.array([m.strength.get() for m in self.__magnets])

    # Sets the values
    def set(self, value: np.array):
        """
        Execute set.

        Parameters
        ----------
        value : np.array
            Input value for this operation.
        """
        nvalue = np.ones(len(self.__magnets)) * value if isinstance(value, float) else value
        for value, m in zip(nvalue, self.__magnets, strict=True):
            m.strength.set(value)

    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value: np.array):
        """
        Execute set_and_wait.

        Parameters
        ----------
        value : np.array
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        """Execute unit."""
        r = []
        for m in self.__magnets:
            r.extend(m.strength.unit())
        return r


class RWMagnetHardwares(ReadWriteFloatArray):
    """
    RWMagnetHardwares configuration or runtime object.

    Parameters
    ----------
    name : str
        Input value for this operation.
    magnets : list[SerializedMagnets]
        Input value for this operation.
    """

    def __init__(self, name: str, magnets: list[SerializedMagnets]):
        """
        Initialize the RWMagnetHardwares.

        Parameters
        ----------
        name : str
            Input value for this operation.
        magnets : list[SerializedMagnets]
            Input value for this operation.
        """
        self.__name = name
        self.__magnets = magnets
        self.__nb = sum(m.get_nb_magnets() for m in magnets)

    # Gets the values
    def get(self) -> np.array:
        """Execute get."""
        return np.array([m.hardware.get() for m in self.__magnets])

    # Sets the values
    def set(self, value: np.array):
        """
        Execute set.

        Parameters
        ----------
        value : np.array
            Input value for this operation.
        """
        nvalue = np.ones(len(self.__magnets)) * value if isinstance(value, float) else value
        for value, m in zip(nvalue, self.__magnets, strict=True):
            m.hardware.set(value)

    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value: np.array):
        """
        Execute set_and_wait.

        Parameters
        ----------
        value : np.array
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        """Execute unit."""
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
    magnets : list[Magnet]
        Magnet list, all elements must be attached to the same instance of
        either a Simulator or a ControlSystem.
    use_aggregator : bool
        Use aggregator to increase performance by using parallel
        access to underlying devices.
    """

    def __init__(
        self,
        arrayName: str,
        magnets: list[SerializedMagnets],
        use_aggregator=False,
    ):
        """
        Initialize the SerializedMagnetsArray.

        Parameters
        ----------
        arrayName : str
            Input value for this operation.
        magnets : list[SerializedMagnets]
            Input value for this operation.
        use_aggregator : object
            Input value for this operation.
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
