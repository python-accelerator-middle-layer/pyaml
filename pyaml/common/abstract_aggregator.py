"""
Abstract Aggregator module.

This module provides abstract aggregator functionality for the PyAML accelerator middle layer.
"""

from abc import ABCMeta, abstractmethod

import numpy as np
import numpy.typing as npt

from .units import AcceptsQuantity


class ScalarAggregator(AcceptsQuantity, metaclass=ABCMeta):
    """
    Abstract class providing access to a list of scalar variables

    Methods
    -------
    set(value)
        Write a list of variable
    set_and_wait(value)
        Write a list of variable and wait that setpoint are reached
    get(quantity=False)
        Return a list variables
    readback()
        Return  a list variables (measurements)
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    @abstractmethod
    def set(self, value: npt.NDArray[np.float64]):
        """Write a list of variable"""
        pass

    @abstractmethod
    def set_and_wait(self, value: npt.NDArray[np.float64]):
        """Write a list of variable and wait that setpoint are reached"""
        pass

    @abstractmethod
    def get(self) -> npt.NDArray[np.float64]:
        """
        Return a list variables.

        Every subclass also accepts ``get(quantity=True)``, which returns the
        values as a :class:`pint.Quantity` in ``unit()``.
        """
        pass

    @abstractmethod
    def readback(self) -> np.array:
        """Return  a list variables (measurements)"""
        pass

    @abstractmethod
    def unit(self) -> str | list[str]:
        """
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().

        A single unit when all values share it, one unit per value only when
        they differ. Unit strings use the pyAML canonical format
        (see :mod:`pyaml.common.units`).
        """
        pass

    def control_system_unit(self) -> str | list[str | None] | None:
        """
        Return the control-system unit for this quantity.

        A single unit when all devices share it, one unit per value only when
        they differ. Same as ``unit()`` by default, for values that no
        control-system device holds. Unit strings use the pyAML canonical format
        (see :mod:`pyaml.common.units`).
        """
        return self.unit()
