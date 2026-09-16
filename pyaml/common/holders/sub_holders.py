"""Specialized holders for accelerator element categories and arrays."""

from typing import TYPE_CHECKING

from ...arrays.bpm_array import BPMArray
from ...arrays.cfm_magnet_array import CombinedFunctionMagnetArray
from ...arrays.magnet_array import MagnetArray
from ...arrays.serialized_magnet_array import SerializedMagnetsArray
from ...bpm.bpm import BPM
from ...magnet.cfm_magnet import CombinedFunctionMagnet
from ...magnet.magnet import Magnet
from ...magnet.serialized_magnet import SerializedMagnets
from .generic_array_holder import GenericArrayHolder
from .generic_element_holder import GenericElementHolder

if TYPE_CHECKING:
    from .element_holder import ElementHolder


class MagnetHolder(GenericElementHolder[Magnet]):
    """
    Provide access to individual magnet elements.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the MagnetHolder.
        """
        super().__init__(peer, peer._MAGNETS, "Magnet")


class MagnetsHolder(GenericArrayHolder[Magnet, MagnetArray]):
    """
    Provide access to arrays of individual magnets.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.

    Notes
    -----
    A configured magnet family is also reachable as an attribute when its
    name is a valid Python identifier, e.g. ``magnets.QuadForTune`` is
    equivalent to ``magnets.get("QuadForTune")``. Family names appear in
    ``dir(magnets)`` for interactive completion.

    Examples
    --------
    >>> quad_family = sr.live.magnets.get("QuadForTune")
    >>> same_quad_family = sr.live.magnets.QuadForTune
    >>> combined_function_magnets = sr.live.magnets.get_cfm()
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the MagnetsHolder.
        """
        super().__init__(
            peer,
            peer._MAGNET_ARRAYS,
            peer.magnet.all,
            peer.magnet.get,
            MagnetArray,
            "Magnet array",
        )

    def get_cfm(self) -> CombinedFunctionMagnetArray:
        """
        Return all combined-function magnets.

        Returns
        -------
        CombinedFunctionMagnetArray
            New unnamed container with every registered combined-function
            magnet.

        Examples
        --------
        >>> combined_function_magnets = sr.live.magnets.get_cfm()
        """
        return self._peer.combined_function_magnets.get()


class CombinedFunctionMagnetHolder(GenericElementHolder[CombinedFunctionMagnet]):
    """
    Provide access to individual combined-function magnets.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the CombinedFunctionMagnetHolder.
        """
        super().__init__(peer, peer._CFM_MAGNETS, "Combined function magnet")


class CombinedFunctionMagnetsHolder(GenericArrayHolder[CombinedFunctionMagnet, CombinedFunctionMagnetArray]):
    """
    Provide access to arrays of combined-function magnets.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.

    Notes
    -----
    A configured array is also reachable as an attribute when its name is a
    valid Python identifier, e.g. ``combined_function_magnets.CFM`` is
    equivalent to ``combined_function_magnets.get("CFM")``. Array names
    appear in ``dir(combined_function_magnets)`` for interactive completion.
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the CombinedFunctionMagnetsHolder.
        """
        super().__init__(
            peer,
            peer._CFM_MAGNET_ARRAYS,
            peer.combined_function_magnet.all,
            peer.combined_function_magnet.get,
            CombinedFunctionMagnetArray,
            "Combined function magnet array",
        )


class SerializedMagnetHolder(GenericElementHolder[SerializedMagnets]):
    """
    Provide access to individual serialized magnet groups.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the SerializedMagnetHolder.
        """
        super().__init__(peer, peer._SERIALIZED_MAGNETS, "Serialized magnet")


class SerializedMagnetsHolder(GenericArrayHolder[SerializedMagnets, SerializedMagnetsArray]):
    """
    Provide access to arrays of serialized magnet groups.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.

    Notes
    -----
    A configured array is also reachable as an attribute when its name is a
    valid Python identifier, e.g. ``serialized_magnets.QForTune`` is
    equivalent to ``serialized_magnets.get("QForTune")``. Array names appear
    in ``dir(serialized_magnets)`` for interactive completion.
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the SerializedMagnetsHolder.
        """
        super().__init__(
            peer,
            peer._SERIALIZED_MAGNETS_ARRAYS,
            peer.serialized_magnet.all,
            peer.serialized_magnet.get,
            SerializedMagnetsArray,
            "serialized magnet array",
        )


class BPMHolder(GenericElementHolder[BPM]):
    """
    Provide access to individual beam-position monitors.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the BPMHolder.
        """
        super().__init__(peer, peer._BPMS, "BPM")


class BPMsHolder(GenericArrayHolder[BPM, BPMArray]):
    """
    Provide access to arrays of beam-position monitors.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder that owns this specialized holder.

    Notes
    -----
    A configured array is also reachable as an attribute when its name is a
    valid Python identifier, e.g. ``bpms.BPMS`` is equivalent to
    ``bpms.get("BPMS")``. Array names appear in ``dir(bpms)`` for interactive
    completion.
    """

    def __init__(self, peer: "ElementHolder"):
        """
        Initialize the BPMsHolder.
        """
        super().__init__(
            peer,
            peer._BPM_ARRAYS,
            peer.bpm.all,
            peer.bpm.get,
            BPMArray,
            "BPM array",
        )
