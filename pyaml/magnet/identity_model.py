import numpy as np
from pydantic import BaseModel,ConfigDict

from .model import MagnetModel
from .. import PyAMLException
from ..configuration.curve import Curve
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "IdentityMagnetModel"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    powerconverter: DeviceAccess|None = None
    """Power converter device to apply current"""
    physics: DeviceAccess|None = None
    """Magnet device to apply strength"""
    unit: str
    """Unit of the strength (i.e. 1/m or m-1)"""

class IdentityMagnetModel(MagnetModel):
    """
    Class that handle magnet current/strength direct access for a single function magnet
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self.__strength_unit = cfg.unit
        self.__ps = None
        self.__hardware_unit = None
        self.__physics = None
        self.__physics_unit = None
        if cfg.powerconverter is not None:
            self.__ps = cfg.powerconverter
            self.__hardware_unit = cfg.powerconverter.unit()
        if cfg.physics is not None:
            self.__physics = cfg.physics
            self.__physics_unit = cfg.physics.unit()

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        raise PyAMLException("The identity model does not support computation")

    def compute_strengths(self, currents: np.array) -> np.array:
        raise PyAMLException("The identity model does not support computation")

    def get_strength_units(self) -> list[str]:
        return [self.__physics_unit] if self.__physics_unit is not None else [""]

    def get_hardware_units(self) -> list[str]:
        return [self.__hardware_unit] if self.__hardware_unit is not None else [""]

    def read_hardware_values(self) -> np.array:
        if self.__ps is None:
            raise PyAMLException(f"{str(self)} does not supports hardware values")
        return [self.__ps.get()]

    def readback_hardware_values(self) -> np.array:
        if self.__ps is None:
            raise PyAMLException(f"{str(self)} does not supports hardware values")
        return [self.__ps.readback()]

    def send_hardware_values(self, currents: np.array):
        if self.__ps is None:
            raise PyAMLException(f"{str(self)} does not supports hardware values")
        self.__ps.set(currents[0])

    def get_devices(self) -> list[DeviceAccess]:
        devices = []
        if self.__ps is not None:
            devices.append(self.__ps)
        if self.__physics is not None:
            devices.append(self.__physics)
        return devices

    def __repr__(self):
        return f"{self.__class__.__name__}(identity {("Magnet" if self.__physics is not None else "Power supply")}, unit={self.__strength_unit})"

    def set_magnet_rigidity(self, brho: np.double):
        pass

    def get_strengths(self) -> np.array:
        if self.__physics is None:
            raise PyAMLException(f"{str(self)} does not supports physics values")
        return np.array([np.float64(self.__physics.get())])

    def set_strengths(self, values:list[float]):
        if self.__physics is None:
            raise PyAMLException(f"{str(self)} does not supports physics values")
        self.__physics.set(values[0])
