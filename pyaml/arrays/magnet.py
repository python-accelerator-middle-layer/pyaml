from .array import ArrayConfigModel,ArrayConfig
from ..control.controlsystem import ControlSystem
from ..lattice.element_holder import ElementHolder

# Define the main class name for this module
PYAMLCLASS = "Magnet"

class ConfigModel(ArrayConfigModel):...

class Magnet(ArrayConfig):

   def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

   def fill_array(self,holder:ElementHolder):   
        holder.fill_magnet_array(self._cfg.name,self._cfg.elements)

   def init_aggregator(self,cs:ControlSystem):
        agg = cs.create_scalar_aggregator()
        if agg is not None:
            # Construct dynamically aggregator for magnets
            mag = cs.get_magnets(self._cfg.name)
            for m in mag:
                devs = m.model.get_devices()
                agg.add_devices(devs)
            mag.set_aggregator(agg)