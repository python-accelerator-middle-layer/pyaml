"""Cfm Magnet module.

This module provides cfm magnet functionality for the PyAML accelerator middle layer.

Notes
-----
The public classes and functions defined here are documented using NumPy-style
docstrings.
"""

from ..common.holders.element_holder import ElementHolder
from ..validation import DynamicValidation, register_schema
from .array import ArrayConfig

# Define the main class name for this module
PYAMLCLASS = "CombinedFunctionMagnet"


@register_schema
class CombinedFunctionMagnet(ArrayConfig, DynamicValidation):
    """
    Combined function magnet array confirguration

    Example
    -------

    A magnet array configuration can also be created by code using
    the following example::

        from pyaml.arrays.cfm_magnet import CombinedFunctionMagnet
        from pyaml.arrays.cfm_magnet import ConfigModel as CFMagnetConfigModel
        magArray = CombinedFunctionMagnet(
                     CFMagnetConfigModel(name="myCFM", elements=["mag1","mag2"])
                   )
    """

    def __init__(self, name: str, elements: list[str]):
        """
        Initialize the CombinedFunctionMagnet.

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
        Fill the combined function magnet array in the element holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with combined function magnet array
        """
        holder.combined_function_magnets.add(self._name, self._elements)
