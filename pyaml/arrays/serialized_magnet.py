from ..common.element_holder import ElementHolder
from ..validation import DynamicValidation, register_schema
from .array import ArrayConfig

# Define the main class name for this module
PYAMLCLASS = "SerializedMagnets"


@register_schema
class SerializedMagnets(ArrayConfig, DynamicValidation):
    """
    Serialized magnets array configuration

    Example
    -------

    A magnet array configuration can also be created by code using
    the following example::

        from pyaml.arrays.serialized_magnet import SerializedMagnets
        from pyaml.arrays.serialized_magnet import ConfigModel as SerializedMagnetConfigModel
        magArray = SerializedMagnets(
                     SerializedMagnetConfigModel(name="mySerializedMagnets", elements=["mag1","mag2"])
                   )
    """

    def __init__(self, name: str, elements: list[str]):
        super().__init__(name, elements)

    def fill_array(self, holder: ElementHolder):
        """
        Fill the serialized magnet array in the element holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with serialized magnet array
        """
        holder.fill_serialized_magnet_array(self._name, self._elements)
