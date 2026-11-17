"""
Knobs of a magnet array.

A tuning tool acts on independent power supplies, its knobs, rather than on magnets: the magnets of a series share
one power supply and form a single knob, their serialized family.
"""

from ..arrays.magnet_array import MagnetArray
from ..common.exception import PyAMLException
from ..magnet.magnet import Magnet


def _is_family(magnet: Magnet) -> bool:
    """Return True for a serialized family: a magnet with no series index whose model is shared by a series."""
    return magnet.series_index is None and magnet.model is not None and magnet.model.shares_power_supply()


def knobs_of(array: MagnetArray) -> MagnetArray:
    """
    Return the knobs of a magnet array, one per independent power supply.

    Each magnet of a series is replaced by its serialized family, so a series gives one knob, named after the family
    and driven through its average strength, however it is listed in the array: one of its magnets, several, all of
    them or the family name. Individually powered magnets and the virtual magnets of a combined-function magnet are
    knobs themselves. Knobs keep the order of first appearance in the array.

    For a series and for an individually powered magnet, ``knobs.hardwares`` gives one power-supply value per knob,
    which saves and restores the state exactly, without going through the excitation curves. A combined-function
    magnet whose matrix links its multipoles to more power supplies has no power-supply value per multipole: its
    knobs are strengths only, and its state is the vector of its power supplies (``cfm.hardwares``). Writing the
    strength of one of its multipoles recomputes all its power supplies through the pseudo-inverse of the matrix.

    Parameters
    ----------
    array : MagnetArray
        Attached magnet array, as configured for the tool.

    Returns
    -------
    MagnetArray
        ``array`` itself when it contains no magnet of a series, otherwise a new array with the same name holding the
        knobs.

    Raises
    ------
    PyAMLException
        If a series mixes magnet functions: it has no single strength and cannot be a knob.
    """
    knobs: list[Magnet] = []
    seen: set[int] = set()
    grouped = False
    for m in array:
        knob = m
        if m.series_index is not None:
            knob = array.get_peer().serialized_magnet.get(m.model_name)
            grouped = True
        if _is_family(knob) and not knob.is_homogeneous():
            raise PyAMLException(
                f"{array.get_name()}: the serialized family {knob.get_name()} mixes magnet functions, it has no single "
                "strength and cannot be a knob of a tuning tool"
            )
        if id(knob) not in seen:
            seen.add(id(knob))
            knobs.append(knob)
    if not grouped:
        return array
    return MagnetArray(array.get_name(), knobs)
