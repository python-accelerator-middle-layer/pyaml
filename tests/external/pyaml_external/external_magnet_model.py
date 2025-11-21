import numpy as np
from pydantic import BaseModel, ConfigDict

from pyaml.control.deviceaccess import DeviceAccess
from pyaml.magnet.model import MagnetModel

# Define the main class name for this module (mandatory)
PYAMLCLASS = "ExternalMagnetModel"


# The ConfigModel (mandatory) indicates what should be inside the associated
# configuration file. Parameters with a default value are optional.
# The ConfigModel structure is then passed to the constructor of the above class


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    powersupply: DeviceAccess
    id: DeviceAccess
    param: str = None


# ConfigModel inherits from pydantic BaseModel
# Take care of having all your private fields prefixed by an `_`


class ExternalMagnetModel(MagnetModel):
    """
    Class example proving manget current/strength conversion
    """

    def __init__(self, cfg: ConfigModel):
        print(
            "ExternalMagnetModel:\n  powersupply:%s\n  id:%s\n  param:%s"
            % (cfg.powersupply.name(), cfg.id.name(), cfg.param)
        )
        self._ps = cfg.powersupply
        self._id = cfg.id
        self._id.set(10)  # Mimic a default value for the gap

    # Implementation of the UnitConv abstract class

    # Get coil current(s) from magnet strength(s)
    def compute_hardware_values(self, strengths: np.array) -> np.array:
        print("ExternalMagnetModel.compute_hardware_values(%f)" % (strengths[0]))
        _gap = self._id.get()
        return np.array([strengths[0] * _gap])

    # Get magnet strength(s) from coil current(s)
    def compute_strengths(self, currents: np.array) -> np.array:
        print("ExternalMagnetModel.compute_strengths(%f)" % (currents[0]))
        _gap = self._id.get()
        return np.array([currents[0] / _gap])

    # Get strength units
    def get_strength_units(self) -> list[str]:
        return ["rad"]

    # Get current units
    def get_hardware_units(self) -> list[str]:
        return ["A"]

    # Get power supply current setpoint(s) from control system
    def read_hardware_values(self) -> np.array:
        return self._ps.get()

    # Get power supply current(s) from control system
    def readback_hardware_values(self) -> np.array:
        pass

    # Send power supply current(s) to control system
    def send_hardware_values(self, currents: np.array):
        self._ps.set(currents)
        pass

    def get_devices(self) -> list[DeviceAccess]:
        return [self._ps, self.id]

    def has_hardware(self) -> bool:
        # No trivial conversion between strength and hardware unit
        return False

    # Set magnet rigidity
    def set_magnet_rigidity(self, brho: np.double):
        pass
