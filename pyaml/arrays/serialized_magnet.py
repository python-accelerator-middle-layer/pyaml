"""
Serialized Magnet module.

This module provides the deprecated serialized magnet array configuration.
"""

import warnings

from ..validation import DynamicValidation, register_schema
from .magnet import Magnet

# Define the main class name for this module
PYAMLCLASS = "SerializedMagnets"


@register_schema
class SerializedMagnets(Magnet, DynamicValidation):
    """
    Serialized magnets array configuration.

    .. deprecated::
        A serialized family is a magnet: use :py:class:`pyaml.arrays.magnet.Magnet`
        (``type: pyaml.arrays.magnet``). This configuration builds the same
        :py:class:`.MagnetArray`, registered with the magnet arrays.

    Parameters
    ----------
    name : str
        Name under which the array is registered and later looked up.
    elements : list[str]
        Element name patterns making up the array: literal names, ``fnmatch`` wildcards, or ``re:`` regular
        expressions.

    Methods
    -------
    fill_array(holder)
        Fill the magnet array in the element holder.
    """

    def __init__(self, name: str, elements: list[str]):
        """
        Initialize the SerializedMagnets.
        """
        warnings.warn(
            f"{name}: pyaml.arrays.serialized_magnet is deprecated, a serialized family is a magnet: use pyaml.arrays.magnet",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(name, elements)
