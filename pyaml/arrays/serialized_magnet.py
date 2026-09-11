"""
Serialized Magnet module.

This module provides serialized magnet functionality.
"""

from ..common.holders.element_holder import ElementHolder
from ..validation import DynamicValidation, register_schema
from .array import ArrayConfig

# Define the main class name for this module
PYAMLCLASS = "SerializedMagnets"


@register_schema
class SerializedMagnets(ArrayConfig, DynamicValidation):
    """
    Serialized magnets array configuration.

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
        Fill the serialized magnet array in the element holder.

    Examples
    --------

    A magnet array configuration can also be created by code using
    the following example::

        from pyaml.arrays.serialized_magnet import SerializedMagnets
        from pyaml.arrays.serialized_magnet import ConfigModel as SerializedMagnetConfigModel
        magArray = SerializedMagnets(
                     SerializedMagnetConfigModel(name="mySerializedMagnets", elements=["mag1","mag2"])
                   )
    """

    def __init__(self, name: str, elements: list[str]):
        """
        Initialize the SerializedMagnets.
        """
        super().__init__(name, elements)

    def fill_array(self, holder: ElementHolder):
        """
        Fill the serialized magnet array in the element holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with serialized magnet array
        """
        holder.serialized_magnets.add(self._name, self._elements)
