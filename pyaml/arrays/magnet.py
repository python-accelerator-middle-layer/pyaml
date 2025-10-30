from .array import ArrayConfigModel,ArrayConfig
from ..common.element_holder import ElementHolder

# Define the main class name for this module
PYAMLCLASS = "Magnet"

class ConfigModel(ArrayConfigModel):...

class Magnet(ArrayConfig):

   def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

   def fill_array(self,holder:ElementHolder):   
        holder.fill_magnet_array(self._cfg.name,self._cfg.elements)
