"""Configuration of a trim coil on a serialized magnet."""

import numpy as np

from ..common.exception import PyAMLException
from ..validation import DynamicValidation, register_schema

PYAMLCLASS = "TrimCoil"


@register_schema
class TrimCoil(DynamicValidation):
    """
    Define a trim coil and its current scaling relative to the main coil.

    Parameters
    ----------
    element : str
        Name of the main series member.
    name : str
        Name of the additional trim magnet.
    powerconverter : str
        Trim power-converter device reference.
    trim_factor : float, optional
        Signed trim-to-main current factor. Must be finite and nonzero.
        Defaults to +1.
    hardware_unit : str or None, optional
        Trim current unit. None inherits the main hardware unit.

    Notes
    -----
    This object describes a coil; it does not create or control a magnet.
    """

    def __init__(
        self,
        element: str,
        name: str,
        powerconverter: str,
        trim_factor: float = 1.0,
        hardware_unit: str | None = None,
    ):
        """Initialize a trim definition."""
        if not element or not name or not powerconverter:
            raise PyAMLException("Trim element, name and powerconverter must be nonempty")
        if not np.isfinite(trim_factor) or trim_factor == 0:
            raise PyAMLException("trim_factor must be finite and nonzero")
        self.element = element
        self.name = name
        self.powerconverter = powerconverter
        self.trim_factor = trim_factor
        self.hardware_unit = hardware_unit
