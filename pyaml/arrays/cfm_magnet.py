from ..common.element_holder import ElementHolder
from .array import ArrayConfig, ArrayConfigModel

# Define the main class name for this module
PYAMLCLASS = "CombinedFunctionMagnet"


class ConfigModel(ArrayConfigModel): ...


class CombinedFunctionMagnet(ArrayConfig):
    """
    Combined function magnet array confirguration

    Example
    -------

    A magnet array configuration can also be created by code using
    the following example::

        from pyaml.arrays.cfm_magnet import CombinedFunctionMagnet
        from pyaml.arrays.cfm_magnet import ConfigModel as CFMagnetConfigModel
        magArray = CombinedFunctionMagnet(
                     CFMagnetConfigModel(name="myCFM", elements=["mag1","mag2"])
                   )
    """

    def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

    def fill_array(self, holder: ElementHolder):
        holder.fill_cfm_magnet_array(self._cfg.name, self._cfg.elements)
