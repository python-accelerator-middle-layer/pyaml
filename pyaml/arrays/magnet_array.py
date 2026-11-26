"""
Magnet Array module.

This module provides magnet array functionality for the PyAML accelerator middle layer.
"""

import time

import numpy as np

from ..common.abstract import ReadWriteFloatArray
from ..common.abstract_aggregator import ScalarAggregator
from ..common.exception import PyAMLException
from ..magnet.magnet import Magnet
from ..magnet.trim_coil_model import TrimCoilModel
from .element_array import ElementArray


def _values_per_magnet(value, nb: int, kind: str) -> np.ndarray:
    """
    Return one value per magnet of the array.

    Parameters
    ----------
    value : float | int | array-like
        A scalar, broadcast to every magnet, or one value per magnet.
    nb : int
        Number of magnets of the array.
    kind : str
        Kind of value (``strength`` or ``hardware``), used in the error message.

    Raises
    ------
    PyAMLException
        If ``value`` is neither a scalar nor a 1-D sequence holding one value per magnet.
    """
    if np.ndim(value) == 0:
        return np.full(nb, float(value))
    values = np.asarray(value, dtype=float)
    if values.ndim != 1 or len(values) != nb:
        raise PyAMLException(f"One {kind} value per magnet is expected ({nb} values), got {np.shape(value)}")
    return values


class RWMagnetStrength(ReadWriteFloatArray):
    """
    Array accessor for the strengths of a magnet family.

    Parameters
    ----------
    name : str
        Name of the array, used when the accessor is reported or logged.
    magnets : list[Magnet]
        Magnets making up the array, in the order their values are read and written.

    Methods
    -------
    get()
        Return the strength of every magnet in the array.
    set(value)
        Set the strength of every magnet in the array.
    set_and_wait(value)
        Set every strength and wait for the readbacks to converge.
    unit()
        Return the strength unit of every magnet in the array.
    set_aggregator(agg)
        Install an aggregator so the array is read and written in a single call.
    """

    def __init__(self, name: str, magnets: list[Magnet]):
        """
        Initialize the RWMagnetStrength.
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
    def set(self, value: np.array, wait_seconds_after: float = None):
        """
        Set the strength of every magnet in the array.

        Parameters
        ----------
        value : np.array
            Strength for each magnet, ordered like the array. A scalar is broadcast to every magnet.

        wait_seconds_after: float
            number of seconds to wait after setting the strengths.
            see also set_and_wait for waiting based on setpoint-readback difference.

        Raises
        ------
        PyAMLException
            If ``value`` is neither a scalar nor one value per magnet. Nothing is written.
        """
        nvalue = _values_per_magnet(value, self.__nb, "strength")
        if not self.__aggregator:
            # Magnets of a series share one power supply: it is written once, from the strengths of the
            # magnets of the series present in the array, the others following the resulting hardware value.
            # A serialized family has no series index: its own strength accessor writes its power supply.
            series: dict[int, tuple[Magnet, dict[int, float]]] = {}
            trims: list[tuple[Magnet, float]] = []
            for idx, m in enumerate(self.__magnets):
                series_index = m.series_index
                if isinstance(m.model, TrimCoilModel):
                    trims.append((m, nvalue[idx]))
                elif series_index is not None:
                    series.setdefault(id(m.model), (m, {}))[1][series_index] = nvalue[idx]
                else:
                    m.strength.set(nvalue[idx])
            for m, requested in series.values():
                current_hardware = np.array([m.hardware.get()])
                m.hardware.set(m.model.compute_hardware_values_partial(current_hardware, requested)[0])
            # Set trims at the final main current, after family and grouped member writes.
            for m, strength in trims:
                m.strength.set(strength)
        else:
            self.__aggregator.set(nvalue)

        # wait the given seconds after setting
        if wait_seconds_after is not None:
            time.sleep(wait_seconds_after)

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

    Methods
    -------
    get()
        Return the hardware value of every magnet in the array.
    set(value)
        Set the hardware value of every magnet in the array.
    set_and_wait(value)
        Set every hardware value and wait for the readbacks to converge.
    unit()
        Return the hardware unit of every magnet in the array.
    set_aggregator(agg)
        Install an aggregator so the array is read and written in a single call.
    """

    def __init__(self, name: str, magnets: list[Magnet]):
        """
        Initialize the RWMagnetHardware.
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

        Raises
        ------
        PyAMLException
            If ``value`` is neither a scalar nor one value per magnet. Nothing is written.
        """
        nvalue = _values_per_magnet(value, self.__nb, "hardware")
        if not self.__aggregator:
            # Magnets of a series share one power supply: it is written once, from the hardware values of the
            # magnets of the series present in the array, the others following it.
            # A serialized family has no series index: its own hardware accessor writes its power supply.
            series: dict[int, tuple[Magnet, dict[int, float]]] = {}
            for idx, m in enumerate(self.__magnets):
                series_index = m.series_index
                if series_index is not None:
                    series.setdefault(id(m.model), (m, {}))[1][series_index] = nvalue[idx]
                else:
                    m.hardware.set(nvalue[idx])
            for m, requested in series.values():
                m.hardware.set(m.model.compute_hardware_from_hardwares(requested))
        else:
            self.__aggregator.set(nvalue)

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
    Class that implements access to a magnet array.

    Parameters
    ----------
    arrayName : str
        Array name
    magnets : list[Magnet]
        Magnet list, all elements must be attached to the same instance of
        either a Simulator or a ControlSystem.
    use_aggregator : bool
        Use aggregator to increase performance by using
        parallel access to underlying devices.

    Attributes
    ----------
    strengths
        Give access to strength of each magnet of this array
    hardwares
        Give access to hardware value of each magnet of this array

    Examples
    --------

    An array can be retrieved from the configuration as in the following example::

        sr = Accelerator.load("acc.yaml")
        quads = sr.design.get_magnets("QuadForTune")
    """

    def __init__(self, arrayName: str, magnets: list[Magnet], use_aggregator=True):
        """
        Initialize the MagnetArray.
        """
        super().__init__(arrayName, magnets, use_aggregator)
        self.__check_families(arrayName, magnets)

        self.__rwstrengths = RWMagnetStrength(arrayName, magnets)
        self.__rwhardwares = RWMagnetHardware(arrayName, magnets)

        if use_aggregator and len(magnets) > 0:
            aggs = self.get_peer().create_magnet_strength_aggregator(magnets)
            aggh = self.get_peer().create_magnet_hardware_aggregator(magnets)
            self.__rwstrengths.set_aggregator(aggs)
            self.__rwhardwares.set_aggregator(aggh)

    @staticmethod
    def __check_families(arrayName: str, magnets: list[Magnet]):
        """
        Raise if a serialized family and one of its magnets are both in the array.

        A family drives every magnet of its series: a magnet of the series cannot also be driven on its own. A family
        is a magnet with no series index whose model is shared by a series, its magnets share the same model.
        """
        families = {
            id(m.model): m for m in magnets if m.model is not None and m.model.shares_power_supply() and m.series_index is None
        }
        for m in magnets:
            family = families.get(id(m.model))
            if family is not None and m is not family:
                raise PyAMLException(
                    f"MagnetArray {arrayName} : {m.get_name()} and {family.get_name()}: a serialized family and its "
                    "magnets cannot be in the same array, the family already drives all its magnets"
                )

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
