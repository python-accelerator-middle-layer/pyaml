import numpy as np
from pydantic import BaseModel, ConfigDict

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier

from .. import PyAMLException
from ..common import abstract
from ..common.element import Element, ElementSchema
from ..control.deviceaccess import DeviceAccess, DeviceAccessSchema
from .rf_transmitter import RFTransmitter, RFTransmitterSchema


class RFPlantSchema(ElementSchema):
    masterclock: DeviceAccessSchema | None = None
    """Device to apply main RF frequency"""
    transmitters: list[RFTransmitterSchema] | None = None
    """List of RF transmitters"""


class RFPlant(Element):
    """
    Main RF object
    """

    def __init__(
        self,
        name: str,
        description: str | None = None,
        lattice_names: str | None = None,
        masterclock: DeviceAccess | None = None,
        transmitters: list[RFTransmitter] | None = None,
    ):
        super().__init__(name, description, lattice_names)
        self._masterclock = masterclock
        self._transmitters = transmitters
        self._frequency = None
        self._voltage = None

    @property
    def frequency(self) -> abstract.ReadWriteFloatScalar:
        if self._frequency is None:
            raise PyAMLException(f"{str(self)} has no masterclock device defined")
        return self._frequency

    @property
    def voltage(self) -> abstract.ReadWriteFloatScalar:
        if self._voltage is None:
            raise PyAMLException(f"{str(self)} has no transmitter device defined")
        return self._voltage

    def attach(
        self,
        peer,
        frequency: abstract.ReadWriteFloatScalar,
        voltage: abstract.ReadWriteFloatScalar,
    ) -> Self:
        # Attach frequency attribute and returns a new reference
        obj = self.__class__(self._name, self._description, self._lattice_names, self._masterclock, self._transmitters)
        obj._frequency = frequency
        obj._voltage = voltage
        obj._peer = peer
        return obj


class RWTotalVoltage(abstract.ReadWriteFloatScalar):
    def __init__(self, transmitters: list[RFTransmitter]):
        """
        Construct a RWTotalVoltage setter

        Parameters
        ----------
        transmitters : list[RFTransmitter]
            List of attached transmitters
        """
        self._trans = transmitters

    def get(self) -> float:
        sum = 0
        # Count only fundamental harmonic
        for t in self._trans:
            if t.harmonic == 1.0:
                sum += t.voltage.get()
        return sum

    def set(self, value: float):
        # Assume that sum of transmitter (fundamental harmonic) distribution is 1
        for t in self._trans:
            if t.harmonic == 1.0:
                v = value * t.distribution
                t.voltage.set(v)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self._trans[0].phase.unit()
