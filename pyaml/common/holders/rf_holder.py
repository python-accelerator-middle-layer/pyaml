"""Holder interfaces for RF plants and their transmitters."""

from typing import TYPE_CHECKING

from ...arrays.element_array import ElementArray
from ...rf.rf_plant import RFPlant
from ...rf.rf_transmitter import RFTransmitter
from ..abstract import ReadWriteFloatScalar
from ..element import __pyaml_repr__
from ..name_matching import is_wildcard, resolve_names

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

    def __getitem__(self, key: str | list[str] | tuple[str, ...]) -> "RFTransmitter | ElementArray":
        """
        Return a transmitter, or a selection typed as a generic ElementArray.

        Parameters
        ----------
        key : str, list[str] or tuple[str, ...]
            An exact literal name returns the stored transmitter. An fnmatch
            wildcard, a ``re:``-prefixed regular expression, or a list/tuple
            of such patterns returns an ElementArray of matches (possibly
            empty).

        Returns
        -------
        RFTransmitter or ElementArray
            The stored transmitter for an exact literal name, otherwise an
            ElementArray of matches.

        Raises
        ------
        PyAMLException
            If an exact literal name, or a literal entry within a list or
            tuple, does not match any transmitter, or a ``re:`` pattern is
            not a valid regular expression.
        """
        store = self._peer._RFTRANSMITTER
        if isinstance(key, str) and not key.startswith("re:") and not is_wildcard(key):
            return self._peer._get("RFTransmitter", key, store)
        names = resolve_names(store.keys(), key, what="RFTransmitter")
        return ElementArray("", [store[n] for n in names])

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
    frequency
        Return the default RF plant's frequency interface.
    voltage
        Return the default RF plant's total-voltage interface.

    Methods
    -------
    get(name)
        Return an RF plant by name.
    add(rf)
        Add an RF plant to the holder.
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
    def frequency(self) -> ReadWriteFloatScalar:
        """Return the default RF plant's frequency interface."""
        return self.get("DEFAULT_RF_PLANT").frequency

    @property
    def voltage(self) -> ReadWriteFloatScalar:
        """Return the default RF plant's total-voltage interface."""
        return self.get("DEFAULT_RF_PLANT").voltage

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

    def __getitem__(self, key: str | list[str] | tuple[str, ...]) -> "RFPlant | ElementArray":
        """
        Return an RF plant, or a selection typed as a generic ElementArray.

        Parameters
        ----------
        key : str, list[str] or tuple[str, ...]
            An exact literal name returns the stored RF plant. An fnmatch
            wildcard, a ``re:``-prefixed regular expression, or a list/tuple
            of such patterns returns an ElementArray of matches (possibly
            empty).

        Returns
        -------
        RFPlant or ElementArray
            The stored RF plant for an exact literal name, otherwise an
            ElementArray of matches.

        Raises
        ------
        PyAMLException
            If an exact literal name, or a literal entry within a list or
            tuple, does not match any RF plant, or a ``re:`` pattern is not
            a valid regular expression.
        """
        store = self._peer._RFPLANT
        if isinstance(key, str) and not key.startswith("re:") and not is_wildcard(key):
            return self._peer._get("RFPlant", key, store)
        names = resolve_names(store.keys(), key, what="RFPlant")
        return ElementArray("", [store[n] for n in names])

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
