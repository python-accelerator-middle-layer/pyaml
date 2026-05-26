"""
Base classes for arrays
"""

from pydantic import BaseModel, ConfigDict

from pyaml.common.exception import PyAMLException

from ..common.element_holder import ElementHolder
from ..validation import ConfigurationSchema, register_schema


class ArraySchema(ConfigurationSchema):
    """
    Schema for configuration of array.

    Parameters
    ----------
    name : str
        Name of the array
    elements : list[str]
        List of element names
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    elements: list[str]


@register_schema(ArraySchema)
class Array:
    """
    Base class that implements configuration for access to arrays (families)
    """

    def __init__(
        self,
        name: str,
        elements: list[str],
    ):
        self._name = name
        self._elements = elements

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

    # def __repr__(self):
    #     # ArrayConfigModel is a super class
    #     # ConfigModel is expected from sub classes
    #     return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
