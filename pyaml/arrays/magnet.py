"""Magnet module.

This module provides magnet functionality for the PyAML accelerator middle layer.
"""

from ..common.holders.element_holder import ElementHolder
from ..validation import DynamicValidation, register_schema
from .array import ArrayConfig

# Define the main class name for this module
PYAMLCLASS = "Magnet"


@register_schema
class Magnet(ArrayConfig, DynamicValidation):
    """
    Magnet array confirguration

    Example
    -------

    A magnet array configuration can also be created by code using
    the following example::

        from pyaml.arrays.magnet import Magnet,ConfigModel as MagnetArrayConfigModel
        magArray = Magnet(
                     MagnetArrayConfigModel(name="MyMags", elements=["mag1","mag2"])
                   )
    """

    def __init__(self, name: str, elements: list[str]):
        """
        Initialize the Magnet.

        Parameters
        ----------
        name : str
            Input value for this operation.
        elements : list[str]
            Input value for this operation.
        """
        super().__init__(name, elements)

    def fill_array(self, holder: ElementHolder):
        """
        Fill the magnet array in the element holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with magnet array
        """
        holder.magnets.add(self._name, self._elements)
