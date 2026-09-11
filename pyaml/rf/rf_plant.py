"""
RF-plant interfaces for accelerator frequency and voltage control.

This module models the master clock and RF transmitters and exposes combined
read/write handles for the plant frequency and total fundamental-harmonic
voltage.
"""

import copy
from typing import TYPE_CHECKING, Self

from .. import PyAMLException
from ..common import abstract
from ..common.element import Element, __pyaml_repr__
from ..validation import DynamicValidation, register_schema
from .rf_transmitter import RFTransmitter

if TYPE_CHECKING:
    from ..common.holders.element_holder import ElementHolder

# Define the main class name for this module
PYAMLCLASS = "RFPlant"


@register_schema
class RFPlant(Element, DynamicValidation):
    """
    Represent an accelerator RF plant and its transmitters.

    The plant exposes frequency and voltage handles after it is attached to a
    simulator or control-system element holder.

    Parameters
    ----------
    name : str
        Name of the RF plant.
    masterclock : str | None
        Name of the master-clock device, if configured.
    transmitters : list[RFTransmitter] | None
        RF transmitters belonging to the plant.
    lattice_names : str | None
        Optional lattice-element mapping.
    description : str | None
        Optional human-readable description.

    Attributes
    ----------
    frequency
        Read/write accessor for the RF frequency, in hertz.
    voltage
        Read/write accessor for the total accelerating voltage, in volts.

    Methods
    -------
    attach(peer, frequency, voltage)
        Return a copy attached to RF read/write handles.
    """

    def __init__(
        self,
        name: str,
        masterclock: str | None = None,
        transmitters: list[RFTransmitter] | None = None,
        lattice_names: str | None = None,
        description: str | None = None,
    ):
        """
        Initialize an RF plant configuration.
        """
        super().__init__(name, lattice_names, description)

        self.masterclock = masterclock
        self.transmitters = transmitters
        self.__frequency = None
        self.__voltage = None

    @property
    def frequency(self) -> abstract.ReadWriteFloatScalar:
        """Return the read/write master-clock frequency handle."""
        if self.__frequency is None:
            raise PyAMLException(f"{str(self.name)} has no masterclock device defined")
        return self.__frequency

    @property
    def voltage(self) -> abstract.ReadWriteFloatScalar:
        """Return the read/write total fundamental-harmonic voltage handle."""
        if self.__voltage is None:
            raise PyAMLException(f"{str(self.name)} has no transmitter device defined")
        return self.__voltage

    def attach(
        self,
        peer,
        frequency: abstract.ReadWriteFloatScalar,
        voltage: abstract.ReadWriteFloatScalar,
    ) -> Self:
        # Attach frequency attribute and returns a new reference
        """
        Return a copy attached to RF read/write handles.

        Parameters
        ----------
        peer : object
            Simulator or control-system element holder.
        frequency : abstract.ReadWriteFloatScalar
            Read/write master-clock frequency handle.
        voltage : abstract.ReadWriteFloatScalar
            Read/write total-voltage handle.

        Returns
        -------
        Self
            Attached RF-plant instance.
        """
        obj = copy.copy(self)
        obj.__frequency = frequency
        obj.__voltage = voltage
        obj._peer = peer
        return obj

    def _fill_device(self, holder: "ElementHolder") -> None:
        holder._fill_rf_plant(self)


class RWTotalVoltage(abstract.ReadWriteFloatScalar):
    """
    Read/write aggregate for fundamental-harmonic transmitter voltage.

    Parameters
    ----------
    transmitters : list[RFTransmitter]
        Transmitters whose fundamental-harmonic voltages are summed.

    Methods
    -------
    get()
        Return the sum of the fundamental-harmonic transmitter voltages.
    set(value)
        Set the total fundamental-harmonic voltage.
    set_and_wait(value)
        Set the total voltage and wait for readback convergence.
    unit()
        Return the voltage unit reported by the first transmitter.
    """

    def __init__(self, transmitters: list[RFTransmitter]):
        """
        Construct an aggregate transmitter-voltage handle.
        """
        self.__trans = transmitters

    def get(self) -> float:
        """Return the sum of the fundamental-harmonic transmitter voltages."""
        sum = 0
        # Count only fundamental harmonic
        for t in self.__trans:
            if t.harmonic == 1.0:
                sum += t.voltage.get()
        return sum

    def set(self, value: float):
        # Assume that sum of transmitter (fundamental harmonic) distribution is 1
        """
        Set the total fundamental-harmonic voltage.

        Parameters
        ----------
        value : float
            Total voltage to distribute among fundamental-harmonic
            transmitters.
        """
        for t in self.__trans:
            if t.harmonic == 1.0:
                v = value * t.distribution
                t.voltage.set(v)

    def set_and_wait(self, value: float):
        """
        Set the total voltage and wait for readback convergence.

        Parameters
        ----------
        value : float
            Requested total voltage.

        Raises
        ------
        NotImplementedError
            This operation is not implemented for aggregate voltage access.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the voltage unit reported by the first transmitter."""
        return self.__trans[0].phase_device_access.unit()

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self, exclude=["frequency", "voltage"])
