from ..common.element_holder import ElementHolder
from .array import ArrayConfig, ArrayConfigModel

# Define the main class name for this module
PYAMLCLASS = "Magnet"


class ConfigModel(ArrayConfigModel): ...


class Magnet(ArrayConfig):
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

    def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

    def fill_array(self, holder: ElementHolder):
        holder.fill_magnet_array(self._cfg.name, self._cfg.elements)
