from .array import ArrayConfigModel,ArrayConfig
from ..lattice.element_holder import ElementHolder

# Define the main class name for this module
PYAMLCLASS = "Magnet"

class ConfigModel(ArrayConfigModel):...

class Magnet(ArrayConfig):

   def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

   def fill_array(self,holder:ElementHolder):   
        holder.fill_magnet_array(self._cfg.name,self._cfg.elements)

   def init_aggregator(self,holder:ElementHolder):
        if self._cfg.aggregator is not None and len(self._cfg.aggregator)==0:
            # Construct dynamically aggregator for magnets
            mag = holder.get_magnets(self._cfg.name)
            for m in mag:
                devs = m.model.get_devices()
                self._cfg.aggregator.add_devices(devs)
            mag.set_aggregator(self._cfg.aggregator)