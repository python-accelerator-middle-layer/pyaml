import copy
from typing import Self

from .. import PyAMLException
from ..common import abstract
from ..common.element import Element
from ..validation import DynamicValidation, register_schema

# Define the main class name for this module
PYAMLCLASS = "RFTransmitter"


@register_schema
class RFTransmitter(Element, DynamicValidation):
    """
    Class that handle a RF transmitter
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
        Get the RF voltage in [V].

        Returns
        -------
        abstract.ReadWriteFloatScalar
            Read/write access to RF voltage

        Raises
        ------
        PyAMLException
            If transmitter is unattached or has no voltage device defined
        """
        if self.__voltage is None:
            raise PyAMLException(f"{str(self.name)} is unattached or has no voltage device defined")
        return self.__voltage

    @property
    def phase(self) -> abstract.ReadWriteFloatScalar:
        """
        Get the RF phase in [rad].

        Returns
        -------
        abstract.ReadWriteFloatScalar
            Read/write access to RF phase

        Raises
        ------
        PyAMLException
            If transmitter is unattached or has no phase device defined
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
        Attach voltage and phase attributes to a peer.

        Parameters
        ----------
        peer : object
            The peer object (simulator or control system)
        voltage : abstract.ReadWriteFloatScalar
            Voltage accessor to attach
        phase : abstract.ReadWriteFloatScalar
            Phase accessor to attach

        Returns
        -------
        Self
            A new attached instance of RFTransmitter
        """
        # Attach voltage and phase attribute and returns a new reference
        obj = copy.copy(self)
        obj.__voltage = voltage
        obj.__phase = phase
        obj._peer = peer
        return obj
