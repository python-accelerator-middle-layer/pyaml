"""
Element module.

This module provides element functionality.
"""

from ..common.holders.element_holder import ElementHolder
from ..validation import DynamicValidation, register_schema
from .array import ArrayConfig

# Define the main class name for this module
PYAMLCLASS = "Element"


@register_schema
class Element(ArrayConfig, DynamicValidation):
    """
    :py:class:`.ElementArray` configuration.

    Examples
    --------

    An element array configuration can also be created by code using
    the following example:

    .. code-block:: python

        from pyaml.arrays.element import Element,ConfigModel as ElementArrayConfigModel
        elt_cfg = Element(
           ElementArrayConfigModel(name="MyArray", elements=["BPM_C04-01","SH1A-C04-H"])
        )
    """

    def __init__(self, name: str, elements: list[str]):
        """
        Initialize the Element.

        Parameters
        ----------
        name : str
            Name under which the array is registered and later looked up.
        elements : list[str]
            Element name patterns making up the array: literal names, ``fnmatch`` wildcards, or ``re:`` regular
            expressions.
        """
        super().__init__(name, elements)

    def fill_array(self, holder: ElementHolder):
        """

        Fill the :py:class:`.ElementArray` using element holder
        (:py:class:`~pyaml.lattice.simulator.Simulator`
        or :py:class:`~pyaml.control.controlsystem.ControlSystem`)
        and add the array to the holder. This method is called when an
        :py:class:`~pyaml.accelerator.Accelerator` is loaded but can be
        used to create arrays by code as shown bellow:

        .. code-block:: python

            >>> elt_cfg.fill_array(sr.design)
            >>> names = sr.design.get_elements("MyArray").names()
            >>> print(names)
            ['BPM_C04-01', 'SH1A-C04-H']

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with element array
        """
        holder.fill_element_array(self._name, self._elements)
