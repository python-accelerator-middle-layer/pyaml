"""RF-transmitter configuration and read/write interfaces.

This module models RF transmitters, their cavity assignments, harmonic and
voltage distribution, and the voltage and phase handles bound on attachment.
"""

import copy
from typing import Self

from .. import PyAMLException
from ..common import abstract
from ..common.element import Element, __pyaml_repr__
from ..validation import DynamicValidation, register_schema

# Define the main class name for this module
PYAMLCLASS = "RFTransmitter"


@register_schema
class RFTransmitter(Element, DynamicValidation):
    """
    Represent an RF transmitter and its cavity controls.

    A transmitter may expose read/write voltage and phase handles after it is
    attached to a simulator or control-system element holder.
    """

    def __init__(
        self,
        name: str,
        cavities: list[str],
        voltage: str | None = None,
        phase: str | None = None,
        harmonic: float = 1.0,
        distribution: float = 1.0,
        lattice_names: str | None = None,
        description: str | None = None,
    ):
        """
        Initialize an RF-transmitter configuration.

        Parameters
        ----------
        name : str
            Name of the transmitter.
        cavities : list[str]
            Names of cavities driven by the transmitter.
        voltage : str | None
            Name of the voltage device, if configured.
        phase : str | None
            Name of the phase device, if configured.
        harmonic : float
            Harmonic number associated with the transmitter.
        distribution : float
            Fraction of aggregate voltage assigned to this transmitter.
        lattice_names : str | None
            Optional lattice-element mapping.
        description : str | None
            Optional human-readable description.
        """
        super().__init__(name, lattice_names, description)
        self.voltage_name = voltage
        self.phase_name = phase
        self.cavities = cavities
        self.harmonic = harmonic
        self.distribution = distribution

        self.__voltage = None
        self.__phase = None

    @property
    def voltage(self) -> abstract.ReadWriteFloatScalar:
        """
        Return the read/write RF-voltage handle in volts.

        Returns
        -------
        abstract.ReadWriteFloatScalar
            Read/write access to the transmitter voltage.

        Raises
        ------
        PyAMLException
            If the transmitter is unattached or has no voltage device.
        """
        if self.__voltage is None:
            raise PyAMLException(f"{str(self.name)} is unattached or has no voltage device defined")
        return self.__voltage

    @property
    def phase(self) -> abstract.ReadWriteFloatScalar:
        """
        Return the read/write RF-phase handle in radians.

        Returns
        -------
        abstract.ReadWriteFloatScalar
            Read/write access to the transmitter phase.

        Raises
        ------
        PyAMLException
            If the transmitter is unattached or has no phase device.
        """
        if self.__phase is None:
            raise PyAMLException(f"{str(self.name)} is unattached or has no phase device defined")
        return self.__phase

    def attach(
        self,
        peer,
        voltage: abstract.ReadWriteFloatScalar,
        phase: abstract.ReadWriteFloatScalar,
    ) -> Self:
        """
        Return a copy with voltage and phase handles attached.

        Parameters
        ----------
        peer : object
            Simulator or control-system element holder.
        voltage : abstract.ReadWriteFloatScalar
            Read/write voltage accessor.
        phase : abstract.ReadWriteFloatScalar
            Read/write phase accessor.

        Returns
        -------
        Self
            Attached copy of the transmitter.
        """
        # Attach voltage and phase attribute and returns a new reference
        obj = copy.copy(self)
        obj.__voltage = voltage
        obj.__phase = phase
        obj._peer = peer
        return obj

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self, exclude=["voltage", "phase"])
