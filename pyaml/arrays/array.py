"""
Array configuration
"""

from pyaml.common.exception import PyAMLException

from ..common.element import __pyaml_repr__
from ..common.holders.element_holder import ElementHolder
from ..validation import DynamicValidation, register_schema


@register_schema
class ArrayConfig(DynamicValidation):
    """
    Base class for configuration of arrays (families).

    Parameters
    ----------
    name : str
        Name of the array
    elements : list[str]
        List of pyaml element names
    """

    def __init__(self, name: str, elements: list[str]):
        """
        Initialize the ArrayConfig.

        Parameters
        ----------
        name : str
            Name of the array
        elements : list[str]
            List of pyaml element names
        """
        self._name = name
        self._elements = elements

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def elements(self):
        """Return the elements."""
        return self._elements

    def fill_array(self, holder: ElementHolder):
        """
        Fill array with elements from the holder and add the array to
        the holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder (:py:class:`~pyaml.lattice.simulator.Simulator`
            or :py:class:`~pyaml.control.controlsystem.ControlSystem`) to
            populate with the array.

        Raises
        ------
        PyAMLException
            When this method is not overridden in a subclass
        """
        raise PyAMLException("Array.fill_array() is not subclassed")

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
