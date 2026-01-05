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
    param: str = None


# ConfigModel inherits from pydantic BaseModel
# Take care of copying yout cfg in `_cfg` field


class ExternalMagnetModel(MagnetModel):
    """
    Class example proving custom manget current/strength conversion.
    """

    def __init__(self, cfg: ConfigModel):
        print(
            "ExternalMagnetModel:\n  powersupply:%s\n  param:%s"
            % (cfg.powersupply.name(), cfg.param)
        )
        self._cfg = cfg

    # Implementation of the MagnetModel abstract class

    # Get hardware value(s) from magnet strength(s)
    def compute_hardware_values(self, strengths: np.array) -> np.array:
        print("ExternalMagnetModel.compute_hardware_values(%f)" % (strengths[0]))
        return np.array([strengths[0] * 10.0])

    # Get magnet strength(s) from hardware values
    def compute_strengths(self, currents: np.array) -> np.array:
        print("ExternalMagnetModel.compute_strengths(%f)" % (currents[0]))
        return np.array([currents[0] / 10.0])

    # Get strength units
    def get_strength_units(self) -> list[str]:
        return ["rad"]

    # Get current units
    def get_hardware_units(self) -> list[str]:
        return ["A"]

    def get_devices(self) -> list[DeviceAccess]:
        return [self._cfg.powersupply]

    def has_hardware(self) -> bool:
        return True

    # Set magnet rigidity
    def set_magnet_rigidity(self, brho: np.double):
        pass
