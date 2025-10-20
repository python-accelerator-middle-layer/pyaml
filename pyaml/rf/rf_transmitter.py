import numpy as np
from pydantic import BaseModel,ConfigDict
try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier

from .. import PyAMLException
from ..control.deviceaccess import DeviceAccess
from ..lattice.element import Element,ElementConfigModel
from ..control import abstract

# Define the main class name for this module
PYAMLCLASS = "RFTransmitter"

class ConfigModel(ElementConfigModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    voltage: DeviceAccess|None = None
    """Device to apply cavity voltage"""
    phase: DeviceAccess|None = None
    """Device to apply cavity phase"""
    cavities: list[str]
    """List of cavity names connected to this transmitter"""
    harmonics: list[int]
    """Harmonic frequency ratio, 1 for main frequency"""
    distribution: float|None = None
    """RF distribution (Part of the total RF powered by this transmitter)"""

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
        if self.__voltage is None:
            raise PyAMLException(f"{str(self)} has no voltage device defined")
        return self.__voltage

    @property
    def phase(self) -> abstract.ReadWriteFloatScalar:
        if self.__phase is None:
            raise PyAMLException(f"{str(self)} has no phase device defined")
        return self.__phase

    def attach(self, voltage: abstract.ReadWriteFloatScalar, phase: abstract.ReadWriteFloatScalar) -> Self:
        # Attach voltage and phase attribute and returns a new reference
        obj = self.__class__(self._cfg)
        obj.__voltage = voltage
        obj.__phase = phase
        return obj

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            self._cfg.name
        )
