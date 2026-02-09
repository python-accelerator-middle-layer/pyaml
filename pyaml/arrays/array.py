"""
Array configuration
"""

from pydantic import BaseModel, ConfigDict

from pyaml.common.exception import PyAMLException

from ..common.element_holder import ElementHolder


class ArrayConfigModel(BaseModel):
    """
    Base class for array configuration

    Parameters
    ----------
    name : str
        Family name
    elements : list[str]
        List of pyaml element names
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    elements: list[str]


class ArrayConfig(object):
    """
    Base class that implements configuration for access to arrays (families)
    """

    def __init__(self, cfg: ArrayConfigModel):
        self._cfg = cfg

    def fill_array(self, holder: ElementHolder):
        """
        Fill array with elements from the holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate

        Raises
        ------
        PyAMLException
            When this method is not overridden in a subclass
        """
        raise PyAMLException("Array.fill_array() is not subclassed")

    def __repr__(self):
        # ArrayConfigModel is a super class
        # ConfigModel is expected from sub classes
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
