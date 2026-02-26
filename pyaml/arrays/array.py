"""
Array configuration
"""

from pydantic import BaseModel, ConfigDict

from pyaml.common.exception import PyAMLException

from ..common.element_holder import ElementHolder


class ArrayConfigModel(BaseModel):
    """
    Base class for configuration of array of :py:class:`~pyaml.arrays.element.Element`,
    :py:class:`~pyaml.arrays.bpm.BPM`, :py:class:`~pyaml.arrays.magnet.Magnet` or
    :py:class:`~pyaml.arrays.cfm_magnet.CombinedFunctionMagnet`.

    Parameters
    ----------
    name : str
        Name of the array
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
        # ArrayConfigModel is a super class
        # ConfigModel is expected from sub classes
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
