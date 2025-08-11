from .array import ArrayConfigModel
from .array import MagnetArrayConfig
from ..lattice.element_holder import ElementHolder,MagnetType

# Define the main class name for this module
PYAMLCLASS = "SkewOctu"

class ConfigModel(ArrayConfigModel):...

class SkewOctu(MagnetArrayConfig):

    def fill_array(self,holder:ElementHolder):
        holder.fill_magnet_array(MagnetType.SKEWOCTU,self._cfg.name,self._cfg.elements)

