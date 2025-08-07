from .array import ArrayConfigModel
from .array import MagnetArrayConfig
from ..lattice.element_holder import ElementHolder,MagnetType

# Define the main class name for this module
PYAMLCLASS = "SkewSext"

class ConfigModel(ArrayConfigModel):...

class SkewSext(MagnetArrayConfig):

    def fill_array(self,holder:ElementHolder):
        holder.fill_magnet_array(MagnetType.SKEWSEXT,self._cfg.name,self._cfg.elements)

