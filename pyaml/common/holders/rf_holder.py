from typing import TYPE_CHECKING

from ...rf.rf_plant import RFPlant
from ...rf.rf_transmitter import RFTransmitter
from ..abstract import ReadWriteFloatScalar

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class RFTransmitterHolder:
    def __init__(self, peer: "ElementHolder"):
        self._peer = peer

    def get(self, name: str) -> RFTransmitter:
        return self._peer._get("RFTransmitter", name, self._peer._RFTRANSMITTER)

    def add(self, rf: RFTransmitter):
        self._peer._add(self._peer._RFTRANSMITTER, rf)


class RFHolder:
    """
    RF holder
    """

    def __init__(self, peer: "ElementHolder"):
        self._peer = peer
        self._rftransmitter_holder = RFTransmitterHolder(peer)

    @property
    def transmitter(self) -> RFTransmitterHolder:
        """
        Returns RF transmitter holder

        Parameters
        ----------
        name : str
            Name of the element
        """
        return self._rftransmitter_holder

    @property
    def frequency(self) -> ReadWriteFloatScalar:
        """
        Return a handle to RF frequency of the DEFAULT_RF_PLANT
        """
        return self.get("DEFAULT_RF_PLANT").frequency

    @property
    def voltage(self) -> ReadWriteFloatScalar:
        """
        Return a handle to RF voltage of the DEFAULT_RF_PLANT
        """
        return self.get("DEFAULT_RF_PLANT").voltage

    def get(self, name: str) -> RFPlant:
        """
        Returns the specified RF plant

        Parameters
        ----------
        name : str
            Name of the RF plant
        """
        return self._peer._get("RFPlant", name, self._peer._RFPLANT)

    def add(self, rf: RFPlant):
        """
        Adds the specified RF plant to the holder

        Parameters
        ----------
        rf : RFPlant
            RF Plant to be added
        """
        self._peer._add(self._peer._RFPLANT, rf)
