from .array import ArrayConfigModel
from .array import MagnetArrayConfig
from ..lattice.element_holder import ElementHolder,MagnetType

# Define the main class name for this module
PYAMLCLASS = "Sextupole"

class ConfigModel(ArrayConfigModel):...

class Sextupole(MagnetArrayConfig):

    def fill_array(self,holder:ElementHolder):
        holder.fill_magnet_array(MagnetType.SEXTUPOLE,self._cfg.name,self._cfg.elements)

