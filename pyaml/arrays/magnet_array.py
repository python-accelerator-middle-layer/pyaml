"""
Magnet Array module.

This module provides magnet array functionality for the PyAML accelerator middle layer.
"""

import numpy as np

from ..common.abstract import ReadWriteFloatArray
from ..common.abstract_aggregator import ScalarAggregator
from ..magnet.magnet import Magnet
from .element_array import ElementArray


class RWMagnetStrength(ReadWriteFloatArray):
    """
    Array accessor for the strengths of a magnet family.

    Parameters
    ----------
    name : str
        Name of the array, used when the accessor is reported or logged.
    magnets : list[Magnet]
        Magnets making up the array, in the order their values are read and written.
    """

    def __init__(self, name: str, magnets: list[Magnet]):
        """
        Initialize the RWMagnetStrength.

        Parameters
        ----------
        name : str
            Name of the array, used when the accessor is reported or logged.
        magnets : list[Magnet]
            Magnets making up the array, in the order their values are read and written.
        """
        self.__name = name
        self.__magnets = magnets
        self.__nb = len(self.__magnets)
        self.__aggregator: ScalarAggregator = None

    # Gets the values
    def get(self) -> np.array:
        """Return the strength of every magnet in the array."""
        if not self.__aggregator:
            return np.array([m.strength.get() for m in self.__magnets])
        else:
            return self.__aggregator.get()

    # Sets the values
    def set(self, value: np.array):
        """
        Set the strength of every magnet in the array.

        Parameters
        ----------
        value : np.array
            Strength for each magnet, ordered like the array. A scalar is broadcast to every magnet.
        """
        nvalue = np.ones(self.__nb) * value if isinstance(value, float) else value
        if not self.__aggregator:
            for idx, m in enumerate(self.__magnets):
                m.strength.set(nvalue[idx])
        else:
            self.__aggregator.set(nvalue)

    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value: np.array):
        """
        Set every strength and wait for the readbacks to converge.

        Parameters
        ----------
        value : np.array
            Strength for each magnet, ordered like the array. A scalar is broadcast to every magnet.

        Raises
        ------
        NotImplementedError
            Waiting for readback convergence is not implemented for this accessor.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        """Return the strength unit of every magnet in the array."""
        return [m.strength.unit() for m in self.__magnets]

    # Set the aggregator (Control system only)
    def set_aggregator(self, agg: ScalarAggregator):
        """
        Install an aggregator so the array is read and written in a single call.

        Parameters
        ----------
        agg : ScalarAggregator
            Aggregator performing grouped device access. Only available on the control-system side; ``None``
            restores per-magnet access.
        """
        self.__aggregator = agg


class RWMagnetHardware(ReadWriteFloatArray):
    """
    Array accessor for the hardware values of a magnet family.

    Parameters
    ----------
    name : str
        Name of the array, used when the accessor is reported or logged.
    magnets : list[Magnet]
        Magnets making up the array, in the order their values are read and written.
    """

    def __init__(self, name: str, magnets: list[Magnet]):
        """
        Initialize the RWMagnetHardware.

        Parameters
        ----------
        name : str
            Name of the array, used when the accessor is reported or logged.
        magnets : list[Magnet]
            Magnets making up the array, in the order their values are read and written.
        """
        self.__name = name
        self.__magnets = magnets
        self.__nb = len(self.__magnets)
        self.__aggregator: ScalarAggregator = None

    # Gets the values
    def get(self) -> np.array:
        """Return the hardware value of every magnet in the array."""
        if not self.__aggregator:
            return np.array([m.hardware.get() for m in self.__magnets])
        else:
            return self.__aggregator.get()

    # Sets the values
    def set(self, value: np.array):
        """
        Set the hardware value of every magnet in the array.

        Parameters
        ----------
        value : np.array
            Hardware value for each magnet, ordered like the array. A scalar is broadcast to every magnet.
        """
        nvalue = np.ones(self.__nb) * value if isinstance(value, float) else value
        if not self.__aggregator:
            for idx, m in enumerate(self.__magnets):
                m.hardware.set(value[idx])
        else:
            self.__aggregator.set(value)

    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value: np.array):
        """
        Set every hardware value and wait for the readbacks to converge.

        Parameters
        ----------
        value : np.array
            Hardware value for each magnet, ordered like the array. A scalar is broadcast to every magnet.

        Raises
        ------
        NotImplementedError
            Waiting for readback convergence is not implemented for this accessor.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> list[str]:
        """Return the hardware unit of every magnet in the array."""
        return [m.hardware.unit() for m in self.__magnets]

    # Set the aggregator
    def set_aggregator(self, agg: ScalarAggregator):
        """
        Install an aggregator so the array is read and written in a single call.

        Parameters
        ----------
        agg : ScalarAggregator
            Aggregator performing grouped device access. Only available on the control-system side; ``None``
            restores per-magnet access.
        """
        self.__aggregator = agg


class MagnetArray(ElementArray):
    """
    Class that implements access to a magnet array

    Parameters
    ----------
    arrayName : str
        Array name
    magnets : list[Magnet]
        Magnet list, all elements must be attached to the same instance of
        either a Simulator or a ControlSystem.
    use_aggregator : bool
        Use aggregator to increase performance by using
        paralell access to underlying devices.

    Examples
    --------

    An array can be retrieved from the configuration as in the following example::

        sr = Accelerator.load("acc.yaml")
        quads = sr.design.get_magnets("QuadForTune")
    """

    def __init__(self, arrayName: str, magnets: list[Magnet], use_aggregator=True):
        """
        Initialize the MagnetArray.

        Parameters
        ----------
        arrayName : str
            Array name
        magnets : list[Magnet]
            Magnet list, all elements must be attached to the same instance of either a Simulator or a ControlSystem.
        use_aggregator : object
            Use aggregator to increase performance by using paralell access to underlying devices.
        """
        super().__init__(arrayName, magnets, use_aggregator)

        self.__rwstrengths = RWMagnetStrength(arrayName, magnets)
        self.__rwhardwares = RWMagnetHardware(arrayName, magnets)

        if use_aggregator and len(magnets) > 0:
            aggs = self.get_peer().create_magnet_strength_aggregator(magnets)
            aggh = self.get_peer().create_magnet_hardware_aggregator(magnets)
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
