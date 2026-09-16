"""Holder interfaces for RF plants and their transmitters."""

from typing import TYPE_CHECKING

from ...rf.rf_plant import RFPlant
from ...rf.rf_transmitter import RFTransmitter
from ..abstract import ReadWriteFloatScalar
from ..element import __pyaml_repr__

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class RFTransmitterHolder:
    """
    Provide name-based access to RF transmitter elements.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent holder containing the transmitter store.

    Methods
    -------
    get(name)
        Return a transmitter by name.
    add(rf)
        Add an RF transmitter to the holder.
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize a transmitter holder for an element holder.
        """
        self._peer = peer

    def get(self, name: str) -> RFTransmitter:
        """
        Return a transmitter by name.

        Parameters
        ----------
        name : str
            Transmitter name.

        Returns
        -------
        RFTransmitter
            Matching RF transmitter.
        """
        return self._peer._get("RFTransmitter", name, self._peer._RFTRANSMITTER)

    def add(self, rf: RFTransmitter):
        """
        Add an RF transmitter to the holder.

        Parameters
        ----------
        rf : RFTransmitter
            Transmitter to add.

        Returns
        -------
        None
            The transmitter is registered in the parent holder in place.
        """
        self._peer._add(self._peer._RFTRANSMITTER, rf)

    def __repr__(self):
        return __pyaml_repr__(self)


class RFHolder:
    """
    Provide access to RF plants and their transmitters.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent holder containing the RF plant store.

    Attributes
    ----------
    transmitter
        Return the holder for RF transmitter elements.
    masterclock
        Return the RF plant configured as ``DEFAULT_RF_PLANT``.
    frequency
        Return the masterclock's frequency interface.
    voltage
        Return the masterclock's total-voltage interface.

    Methods
    -------
    get(name)
        Return an RF plant by name.
    add(rf)
        Add an RF plant to the holder.

    Notes
    -----
    ``frequency`` and ``voltage`` are backward-compatible aliases for
    ``masterclock.frequency`` and ``masterclock.voltage``. Do not confuse
    this ``masterclock`` (the default :class:`~pyaml.rf.rf_plant.RFPlant`
    object) with :attr:`~pyaml.rf.rf_plant.RFPlant.masterclock` (the
    master-clock device name configured on an ``RFPlant``).

    Examples
    --------
    >>> masterclock = sr.live.rf.masterclock
    >>> masterclock.frequency.set(499.654e6)
    >>> masterclock.voltage.set(2.5e6)
    >>> same_frequency = sr.live.rf.frequency
    >>> spare_rf_plant = sr.live.rf.get("SPARE_RF_PLANT")
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize an RF holder for an element holder.
        """
        self._peer = peer
        self._rftransmitter_holder = RFTransmitterHolder(peer)

    @property
    def transmitter(self) -> RFTransmitterHolder:
        """Return the holder for RF transmitter elements."""
        return self._rftransmitter_holder

    @property
    def masterclock(self) -> RFPlant:
        """
        Return the RF plant configured as ``DEFAULT_RF_PLANT``.

        Returns
        -------
        RFPlant
            RF plant registered under ``DEFAULT_RF_PLANT``.

        Raises
        ------
        PyAMLException
            If no RF plant is registered under ``DEFAULT_RF_PLANT``.

        Examples
        --------
        >>> masterclock = sr.live.rf.masterclock
        >>> masterclock.frequency.set(499.654e6)
        """
        return self.get("DEFAULT_RF_PLANT")

    @property
    def frequency(self) -> ReadWriteFloatScalar:
        """Return the masterclock's frequency interface (alias for ``masterclock.frequency``)."""
        return self.masterclock.frequency

    @property
    def voltage(self) -> ReadWriteFloatScalar:
        """Return the masterclock's total-voltage interface (alias for ``masterclock.voltage``)."""
        return self.masterclock.voltage

    def get(self, name: str) -> RFPlant:
        """
        Return an RF plant by name.

        Parameters
        ----------
        name : str
            RF plant name.

        Returns
        -------
        RFPlant
            RF plant registered under ``name``.
        """
        return self._peer._get("RFPlant", name, self._peer._RFPLANT)

    def add(self, rf: RFPlant):
        """
        Add an RF plant to the holder.

        Parameters
        ----------
        rf : RFPlant
            RF plant to add.

        Returns
        -------
        None
            The plant is registered in the parent holder in place.
        """
        self._peer._add(self._peer._RFPLANT, rf)

    def __repr__(self):
        return __pyaml_repr__(self)
