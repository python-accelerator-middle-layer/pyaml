from ..common.element_holder import ElementHolder
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
        super().__init__(name, elements)

    def fill_array(self, holder: ElementHolder):
        """
        Fill the magnet array in the element holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with magnet array
        """
        holder.fill_magnet_array(self._name, self._elements)
