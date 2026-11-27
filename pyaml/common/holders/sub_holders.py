"""Specialized holders for accelerator element families and their arrays."""

from typing import TYPE_CHECKING

from pyaml.diagnostics.bpm import BPM

from ...arrays.bpm_array import BPMArray
from ...arrays.cfm_magnet_array import CombinedFunctionMagnetArray
from ...arrays.magnet_array import MagnetArray
from ...magnet.cfm_magnet import CombinedFunctionMagnet
from ...magnet.magnet import Magnet
from ...magnet.serialized_magnet import SerializedMagnets
from .generic_holder import GenericHolder

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class MagnetHolder(GenericHolder[Magnet, MagnetArray]):
    """
    Provide access to individual magnets and to configured magnet arrays.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.

    Notes
    -----
    :meth:`get`, ``[key]`` and :meth:`get_array` without a name see the
    individual magnets. A serialized family is reached through
    ``holder.serialized_magnet``.

    A configured magnet array is also reachable as an attribute when its name
    is a valid Python identifier, e.g. ``magnet.QuadForTune`` is equivalent to
    ``magnet.get_array("QuadForTune")``. Array names appear in ``dir(magnet)``
    for interactive completion.

    A serialized family name in a configured array stands for one magnet, the
    family itself. Its magnets are not added to the array, and excluding one
    of them while the family is in the array raises an error.

    Examples
    --------
    >>> quad = sr.live.magnet.get("QF1A-C01")
    >>> quad_family = sr.live.magnet.get_array("QuadForTune")
    >>> same_quad_family = sr.live.magnet.QuadForTune
    >>> all_magnets = sr.live.magnet.get_array()
    >>> some_quads = sr.live.magnet["QF1*"]
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the MagnetHolder.
        """
        super().__init__(
            peer,
            peer._MAGNETS,
            peer._MAGNET_ARRAYS,
            MagnetArray,
            "Magnet",
            resolver=self.__resolve_array_member,
            members_func=self.__family_members,
        )

    def __resolve_array_member(self, name: str) -> Magnet:
        """Resolve a magnet or a serialized family listed in a configured array."""
        if name in self._peer._SERIALIZED_MAGNETS:
            return self._peer._SERIALIZED_MAGNETS[name]
        return self.get(name)

    def __family_members(self, name: str) -> list[str] | None:
        """Return the magnet names of a serialized family, ``None`` for another element."""
        family = self._peer._SERIALIZED_MAGNETS.get(name)
        return None if family is None else family.names()


class CombinedFunctionMagnetHolder(GenericHolder[CombinedFunctionMagnet, CombinedFunctionMagnetArray]):
    """
    Provide access to combined-function magnets and to their configured arrays.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.

    Notes
    -----
    A configured array is also reachable as an attribute when its name is a
    valid Python identifier, e.g. ``combined_function_magnet.CFM`` is
    equivalent to ``combined_function_magnet.get_array("CFM")``. Array names
    appear in ``dir(combined_function_magnet)`` for interactive completion.

    Examples
    --------
    >>> cfm = sr.live.combined_function_magnet.get("SH1A-C01")
    >>> all_cfms = sr.live.combined_function_magnet.get_array()
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the CombinedFunctionMagnetHolder.
        """
        super().__init__(
            peer,
            peer._CFM_MAGNETS,
            peer._CFM_MAGNET_ARRAYS,
            CombinedFunctionMagnetArray,
            "Combined function magnet",
        )


class SerializedMagnetHolder(GenericHolder[SerializedMagnets, MagnetArray]):
    """
    Provide access to serialized magnet families.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.

    Notes
    -----
    A serialized family is a magnet, so it has no array store of its own:
    configured arrays are shared with ``holder.magnet`` and :meth:`get_array`
    with a name looks them up there. :meth:`get_array` without a name returns
    every family.

    Examples
    --------
    >>> family = sr.live.serialized_magnet.get("QF1-SERIES")
    >>> all_families = sr.live.serialized_magnet.get_array()
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the SerializedMagnetHolder.
        """
        super().__init__(
            peer,
            peer._SERIALIZED_MAGNETS,
            peer._MAGNET_ARRAYS,
            MagnetArray,
            "Serialized magnet",
        )


class BPMHolder(GenericHolder[BPM, BPMArray]):
    """
    Provide access to beam-position monitors and to configured BPM arrays.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.

    Notes
    -----
    A configured array is also reachable as an attribute when its name is a
    valid Python identifier, e.g. ``bpm.BPMS`` is equivalent to
    ``bpm.get_array("BPMS")``. Array names appear in ``dir(bpm)`` for
    interactive completion.

    Examples
    --------
    >>> bpm = sr.live.diagnostic.bpm.get("BPM_C01-01")
    >>> bpms = sr.live.diagnostic.bpm.get_array("BPMS")
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the BPMHolder.
        """
        super().__init__(peer, peer._BPMS, peer._BPM_ARRAYS, BPMArray, "BPM")
