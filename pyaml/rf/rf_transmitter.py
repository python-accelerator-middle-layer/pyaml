import numpy as np
from pydantic import BaseModel, ConfigDict

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier

from .. import PyAMLException
from ..common import abstract
from ..common.element import Element, ElementConfigModel
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "RFTransmitter"


class ConfigModel(ElementConfigModel):
    """
    Configuration model for RF Transmitter.

    Attributes
    ----------
    voltage : DeviceAccess or None, optional
        Device to apply cavity voltage
    phase : DeviceAccess or None, optional
        Device to apply cavity phase
    cavities : list[str]
        List of cavity names connected to this transmitter
    harmonic : float, optional
        Harmonic frequency ratio, 1.0 for main frequency, by default 1.0
    distribution : float, optional
        RF distribution (Part of the total RF voltage powered by this transmitter),
        by default 1.0
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    voltage: DeviceAccess | None = None
    phase: DeviceAccess | None = None
    cavities: list[str]
    harmonic: float = 1.0
    distribution: float = 1.0


class RFTransmitter(Element):
    """
    Class that handle a RF transmitter
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg
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
            raise PyAMLException(
                f"{str(self)} is unattached or has no voltage device defined"
            )
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
            raise PyAMLException(
                f"{str(self)} is unattached or has no phase device defined"
            )
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
        obj = self.__class__(self._cfg)
        obj.__voltage = voltage
        obj.__phase = phase
        obj._peer = peer
        return obj
