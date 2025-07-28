from pydantic import BaseModel
import numpy as np
from pyaml.magnet.model import MagnetModel
from pyaml.control.deviceaccess import DeviceAccess


# Define the main class name for this module (mandatory)
PYAMLCLASS = "ExternalUnitConv"


# The ConfigModel (mandatory) indicates what should be inside the associated
# configuration file. Parameters with a default value are optional.
# The ConfigModel structure is then passed to the constructor of the above class

class ConfigModel(BaseModel):

    powersupply: DeviceAccess
    id: DeviceAccess
    param: str = None

# UnitConv inherits from pydantic BaseModel
# Take care of having all your private fields prefixed by an `_`

class ExternalUnitConv(MagnetModel):
    """
    Class example proving manget current/strength conversion
    """

    def __init__(self, cfg: ConfigModel):
        print("ExternalUnitConv:\n  powersupply:%s\n  id:%s\n  param:%s" 
              % (cfg.powersupply.name(),cfg.id.name(),cfg.param))
        self._ps = cfg.powersupply
        self._id = cfg.id
        self._id.set(10) # Mimic a default value for the gap
 
    # Implementation of the UnitConv abstract class

    # Get coil current(s) from magnet strength(s)
    def compute_hardware_values(self,strengths:np.array) -> np.array:
        print("ExternalUnitConv.compute_currents(%f)" % (strengths[0]))
        _gap = self._id.get()
        return np.array([strengths[0]*_gap])

    # Get magnet strength(s) from coil current(s)
    def compute_strengths(self,currents:np.array) -> np.array:
        print("ExternalUnitConv.compute_strengths(%f)" % (currents[0]))
        _gap = self._id.get()
        return np.array([currents[0]/_gap])

    # Get strength units
    def get_strength_units(self) -> list[str]:
        return["rad"]

    # Get current units
    def get_hardware_units(self) -> list[str]:
        return["A"]

    # Get power supply current setpoint(s) from control system
    def read_hardware_values(self) -> np.array:
        return self._ps.get()

    # Get power supply current(s) from control system
    def readback_hardware_values(self) -> np.array:
        pass

    # Send power supply current(s) to control system
    def send_harware_values(self,currents:np.array):
        self._ps.set(currents)
        pass

    # Set magnet rigidity
    def set_magnet_rigidity(self,brho:np.double):
        pass

