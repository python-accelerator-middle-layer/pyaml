"""
Magnet module.

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
    :py:class:`.MagnetArray` configuration.

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

    Notes
    -----
    A serialized family (:py:class:`~pyaml.magnet.serialized_magnet.SerializedMagnets`) is a magnet: its name,
    or a pattern matching it, adds one element to the array, the family, which reads and writes the average
    strength and the power-supply current of its series. The magnets of the family are not added, even when
    listed explicitly or matched by the same pattern: they are already driven through the family.

    - ``~FAMILY`` excludes the family and its magnets.
    - Excluding one magnet of a family which is in the array raises an error: a series cannot be split. List the
      individual magnets of the series instead to drive a part of it.

    .. code-block:: yaml

        - type: pyaml.arrays.magnet
          name: QForTune
          elements:
            - QF1A          # serialized family: one element
            - QF1A-C05      # magnet of QF1A: already driven by the family, not added
            - QD2*          # individual quadrupoles and families matching the pattern

    Examples
    --------

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
