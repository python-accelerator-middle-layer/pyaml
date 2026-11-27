"""
Combined function magnet array module.

This module provides combined function magnet array functionality.
"""

import numpy as np

from ..common.abstract import ReadWriteFloatArray
from ..common.exception import PyAMLException
from ..common.units import common_unit, per_value_units
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from .element_array import ElementArray

# TODO handle aggregator for CFM


class RWMagnetStrengths(ReadWriteFloatArray):
    """
    Array accessor for the multipole strengths of combined-function magnets.

    Parameters
    ----------
    name : str
        Name of the array, used when the accessor is reported or logged.
    magnets : list[CombinedFunctionMagnet]
        Combined-function magnets making up the array; each contributes one entry per multipole.

    Methods
    -------
    get()
        Return the strength of every multipole, concatenated over the magnets.
    set(value)
        Set the strength of every multipole, concatenated over the magnets.
    set_and_wait(value)
        Set every multipole strength and wait for the readbacks to converge.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    """

    def __init__(self, name: str, magnets: list[CombinedFunctionMagnet]):
        """
        Initialize the RWMagnetStrengths.
        """
        self.__name = name
        self.__magnets = magnets
        self.__nb = sum(m.nb_multipole() for m in magnets)

    # Gets the values
    def get(self) -> np.array:
        """Return the strength of every multipole, concatenated over the magnets."""
        r = np.zeros(self.__nb)
        idx = 0
        for m in self.__magnets:
            r[idx : idx + m.nb_multipole()] = m.strengths.get()
            idx += m.nb_multipole()
        return r

    # Sets the values
    def set(self, value: np.array):
        """
        Set the strength of every multipole, concatenated over the magnets.

        Parameters
        ----------
        value : np.array
            Strength of every multipole, concatenated magnet by magnet. A scalar is broadcast to all of them.
        """
        nvalue = np.ones(self.__nb) * value if isinstance(value, float) else value
        idx = 0
        for m in self.__magnets:
            m.strengths.set(nvalue[idx : idx + m.nb_multipole()])
            idx += m.nb_multipole()

    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value: np.array):
        """
        Set every multipole strength and wait for the readbacks to converge.

        Parameters
        ----------
        value : np.array
            Strength of every multipole, concatenated magnet by magnet. A scalar is broadcast to all of them.

        Raises
        ------
        NotImplementedError
            Waiting for readback convergence is not implemented for this accessor.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> str | list[str]:
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        units = []
        for m in self.__magnets:
            units.extend(per_value_units(m.strengths.unit(), len(m.model.get_strength_units())))
        return common_unit(units)


class RWMagnetHardwares(ReadWriteFloatArray):
    """
    Array accessor for the hardware values of combined-function magnets.

    Parameters
    ----------
    name : str
        Name of the array, used when the accessor is reported or logged.
    magnets : list[CombinedFunctionMagnet]
        Combined-function magnets making up the array; each contributes one entry per multipole.

    Methods
    -------
    get()
        Return the hardware value of every multipole, concatenated over the magnets.
    set(value)
        Set the hardware value of every multipole, concatenated over the magnets.
    set_and_wait(value)
        Set every hardware value and wait for the readbacks to converge.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(self, name: str, magnets: list[CombinedFunctionMagnet]):
        """
        Initialize the RWMagnetHardwares.
        """
        self.__name = name
        self.__magnets = magnets
        self.__nb = sum(m.nb_multipole() for m in magnets)

    # Gets the values
    def get(self) -> np.array:
        """Return the hardware value of every multipole, concatenated over the magnets."""
        r = np.zeros(self.__nb)
        idx = 0
        for m in self.__magnets:
            r[idx : idx + m.nb_multipole()] = m.hardwares.get()
            idx += m.nb_multipole()
        return r

    # Sets the values
    def set(self, value: np.array):
        """
        Set the hardware value of every multipole, concatenated over the magnets.

        Parameters
        ----------
        value : np.array
            Hardware value of every multipole, concatenated magnet by magnet. A scalar is broadcast to all of them.
        """
        nvalue = np.ones(self.__nb) * value if isinstance(value, float) else value
        idx = 0
        for m in self.__magnets:
            m.hardwares.set(nvalue[idx : idx + m.nb_multipole()])
            idx += m.nb_multipole()

    # Sets the values and waits that the read values reach their setpoint
    def set_and_wait(self, value: np.array):
        """
        Set every hardware value and wait for the readbacks to converge.

        Parameters
        ----------
        value : np.array
            Hardware value of every multipole, concatenated magnet by magnet. A scalar is broadcast to all of them.

        Raises
        ------
        NotImplementedError
            Waiting for readback convergence is not implemented for this accessor.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the values
    def unit(self) -> str | list[str]:
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        units = []
        for m in self.__magnets:
            units.extend(per_value_units(m.hardwares.unit(), len(m.model.get_hardware_units())))
        return common_unit(units)

    def control_system_unit(self) -> str | list[str | None] | None:
        """Return the control-system unit for this quantity."""
        units = []
        for m in self.__magnets:
            units.extend(per_value_units(m.hardwares.control_system_unit(), len(m.model.get_hardware_units())))
        return common_unit(units)


class CombinedFunctionMagnetArray(ElementArray):
    """
    Class that implements access to a combined function magnet array

    Parameters
    ----------
    arrayName : str
        Array name
    magnets : list[CombinedFunctionMagnet]
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
        magnets: list[CombinedFunctionMagnet],
        use_aggregator=False,
    ):
        """
        Initialize the CombinedFunctionMagnetArray.
        """
        super().__init__(arrayName, magnets, use_aggregator)

        self.__rwstrengths = RWMagnetStrengths(arrayName, magnets)
        self.__rwhardwares = RWMagnetHardwares(arrayName, magnets)

        if use_aggregator:
            raise (PyAMLException("Aggregator not implemented for CombinedFunctionMagnetArray"))

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
