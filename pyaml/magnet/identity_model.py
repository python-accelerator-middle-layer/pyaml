from .model import MagnetModel
from .. import PyAMLException
from ..control.deviceaccess import DeviceAccess
from ..common.element import __pyaml_repr__

import numpy as np
from pydantic import BaseModel,ConfigDict

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
    Class that map value to underlying device without conversion
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self.__unit = cfg.unit
        if cfg.physics is None and cfg.powerconverter is None:
            raise PyAMLException("Invalid IdentityMagnetModel configuration, physics or powerconverter device required")
        if cfg.physics is not None and cfg.powerconverter is not None:
            raise PyAMLException("Invalid IdentityMagnetModel configuration, physics or powerconverter device required but not both")
        if cfg.physics:
            self.__device = cfg.physics
        else:
            self.__device = cfg.powerconverter

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        return strengths

    def compute_strengths(self, currents: np.array) -> np.array:
        return currents

    def get_strength_units(self) -> list[str]:
        return [self.__unit]

    def get_hardware_units(self) -> list[str]:
        return [self.__unit]

    def read_hardware_values(self) -> np.array:
        return [self.__device.get()]

    def readback_hardware_values(self) -> np.array:
        return [self.__device.readback()]

    def send_hardware_values(self, currents: np.array):
        self.__device.set(currents[0])

    def get_devices(self) -> list[DeviceAccess]:
        return [self.__device]

    def set_magnet_rigidity(self, brho: np.double):
        pass

    def has_physics(self) -> bool:
        return self._cfg.physics is not None

    def has_hardware(self) -> bool:
        return self._cfg.powerconverter is not None

    def __repr__(self):
       return __pyaml_repr__(self)
