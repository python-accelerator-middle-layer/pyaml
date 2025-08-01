from .array import ArrayModel
from .array import Array
from ..lattice.element_holder import ElementHolder,MagnetType

# Define the main class name for this module
PYAMLCLASS = "Sextupole"

class ConfigModel(ArrayModel):...

class Sextupole(Array):
    """
    Class that implements access to arrays (families)
    """
    def __init__(self, cfg: ArrayModel):
        super().__init__(cfg)

    def fill_array(self,holder:ElementHolder):
        holder.fill_magnet_array(MagnetType.SEXTUPOLE,self._cfg.name,self._cfg.elements)

