from ..common.element_holder import ElementHolder
from .array import ArrayConfig, ArrayConfigModel

# Define the main class name for this module
PYAMLCLASS = "SerializedMagnets"


class ConfigModel(ArrayConfigModel):
    """Configuration model for Serialized Magnets array."""
    ...


class SerializedMagnets(ArrayConfig):
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

    def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

    def fill_array(self, holder: ElementHolder):
        """
        Fill the serialized magnet array in the element holder.

        Parameters
        ----------
        holder : ElementHolder
            The element holder to populate with serialized magnet array
        """
        holder.fill_serialized_magnet_array(self._cfg.name, self._cfg.elements)
