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
    magnets: list[DeviceAccess]|None = None
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
        self.__magnets = None
        self.__magnet_unit = None
        if cfg.powerconverters is not None:
            self.__ps = cfg.powerconverters
            self.__hardware_unit = [powerconverter.unit() for powerconverter in cfg.powerconverters]
        if cfg.magnets is not None:
            self.__magnets = cfg.magnets
            self.__magnet_unit = [magnet.unit() for magnet in cfg.magnets]

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        raise PyAMLException("The identity model does not support computation")

    def compute_strengths(self, currents: np.array) -> np.array:
        raise PyAMLException("The identity model does not support computation")

    def get_strength_units(self) -> list[str]:
        return [self.__magnet_unit] if self.__magnet_unit is not None else [""]

    def get_hardware_units(self) -> list[str]:
        return [p.unit() for p in self._cfg.powerconverters] if self.__hardware_unit is not None else [""]

    def read_hardware_values(self) -> np.array:
        if self.__ps is None:
            raise PyAMLException(f"{str(self)} does not supports physics values")
        return [self.__ps.get()]

    def readback_hardware_values(self) -> np.array:
        if self.__ps is None:
            raise PyAMLException(f"{str(self)} does not supports hardware values")
        return [ps.readback() for ps in self.__ps]

    def send_hardware_values(self, currents: np.array):
        if self.__ps is None:
            raise PyAMLException(f"{str(self)} does not hardware physics values")
        [ps.set(currents) for ps in self.__ps]

    def get_devices(self) -> list[DeviceAccess]:
        devices = []
        if self.__ps is not None:
            devices.extend(self.__ps)
        if self.__magnets is not None:
            devices.extend(self.__magnets)
        return devices

    def __repr__(self):
        return f"{self.__class__.__name__}(identity {("Magnet" if self.__magnets is not None else "Power supply")}, unit={self.__strength_unit})"

    def set_magnet_rigidity(self, brho: np.double):
        pass

