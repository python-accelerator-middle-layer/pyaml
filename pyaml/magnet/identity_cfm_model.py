import numpy as np
from pydantic import BaseModel,ConfigDict

from .model import MagnetModel
from .. import PyAMLException
from ..configuration.curve import Curve
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "IdentityCFMagnetModel"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    multipoles: list[str]
    """List of supported functions: A0,B0,A1,B1,etc (i.e. [B0,A1,B2])"""
    powerconverters: list[DeviceAccess]|None = None
    """Power converter device to apply current"""
    physics: list[DeviceAccess] | None = None
    """Magnet device to apply strength"""
    units: list[str]
    """List of strength unit (i.e. ['rad','m-1','m-2'])"""

class IdentityCFMagnetModel(MagnetModel):
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
        if cfg.powerconverters is not None:
            self.__ps = cfg.powerconverters
            self.__hardware_unit = [powerconverter.unit() for powerconverter in cfg.powerconverters]
        if cfg.physics is not None:
            self.__physics = cfg.physics
            self.__physics_unit = [magnet.unit() for magnet in cfg.physics]

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        raise PyAMLException("The identity model does not support computation")

    def compute_strengths(self, currents: np.array) -> np.array:
        raise PyAMLException("The identity model does not support computation")

    def get_strength_units(self) -> list[str]:
        return [self.__physics_unit] if self.__physics_unit is not None else [""]

    def get_hardware_units(self) -> list[str]:
        return [p.unit() for p in self._cfg.powerconverters] if self.__hardware_unit is not None else [""]

    def read_hardware_values(self) -> np.array:
        if self.__ps is None:
            raise PyAMLException(f"{str(self)} does not supports hardware values")
        return [self.__ps.get()]

    def readback_hardware_values(self) -> np.array:
        if self.__ps is None:
            raise PyAMLException(f"{str(self)} does not supports hardware values")
        return [ps.readback() for ps in self.__ps]

    def send_hardware_values(self, currents: np.array):
        if self.__ps is None:
            raise PyAMLException(f"{str(self)} does not hardware hardware values")
        [ps.set(currents) for ps in self.__ps]

    def get_devices(self) -> list[DeviceAccess]:
        devices = []
        if self.__ps is not None:
            devices.extend(self.__ps)
        if self.__physics is not None:
            devices.extend(self.__physics)
        return devices

    def __repr__(self):
        return f"{self.__class__.__name__}(identity {("Magnet" if self.__physics is not None else "Power supply")}, unit={self.__strength_unit})"

    def set_magnet_rigidity(self, brho: np.double):
        pass

    def get_strengths(self) -> np.array:
        if self.__physics is None:
            raise PyAMLException(f"{str(self)} does not supports physics values")
        return np.array([np.float64(magnet.get()) for magnet in self.__physics])

    def set_strengths(self, values:list[float]):
        if self.__physics is None:
            raise PyAMLException(f"{str(self)} does not supports physics values")
        for value, magnet in zip(values, self.__physics):
            magnet.set(value)
