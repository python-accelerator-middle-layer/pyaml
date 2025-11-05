import numpy as np
from pydantic import BaseModel,ConfigDict

from .model import MagnetModel
from .. import PyAMLException
from ..control.deviceaccess import DeviceAccess
from ..common.element import __pyaml_repr__

# Define the main class name for this module
PYAMLCLASS = "IdentityCFMagnetModel"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    multipoles: list[str]
    """List of supported functions: A0,B0,A1,B1,etc (i.e. [B0,A1,B2])"""
    powerconverters: list[DeviceAccess] | None = None
    """Power converter device to apply current"""
    physics: list[DeviceAccess] | None = None
    """Magnet device to apply strength"""
    units: list[str]
    """List of strength unit (i.e. ['rad','m-1','m-2'])"""

class IdentityCFMagnetModel(MagnetModel):
    """
    Class that map values to underlying devices without conversion
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

        # Check config
        self.__nbFunction: int = len(cfg.multipoles)

        if cfg.physics is None and cfg.powerconverters is None:
            raise PyAMLException("Invalid IdentityCFMagnetModel configuration, physics or powerconverters device required")
        if cfg.physics is not None and cfg.powerconverters is not None:
            raise PyAMLException("Invalid IdentityCFMagnetModel configuration, physics or powerconverters device required but not both")
        if cfg.physics:
            self.__devices = cfg.physics
        else:
            self.__devices = cfg.powerconverters

        self.__nbDev: int = len(self.__devices)

        self.__check_len(cfg.units,"units",self.__nbFunction)

    def __check_len(self,obj,name,expected_len):
        lgth = len(obj) 
        if lgth != expected_len:
            raise PyAMLException(
                f"{name} does not have the expected "
                f"number of items ({expected_len} items expected but got {lgth})"
            )    

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        return strengths

    def compute_strengths(self, currents: np.array) -> np.array:
        return currents

    def get_strength_units(self) -> list[str]:
        return self._cfg.units

    def get_hardware_units(self) -> list[str]:
        return self._cfg.units

    def read_hardware_values(self) -> np.array:
        return np.array([p.get() for p in self.__devices])

    def readback_hardware_values(self) -> np.array:
        return np.array([p.readback() for p in self.__devices])

    def send_hardware_values(self, currents: np.array):
        for idx, p in enumerate(self.__devices):
            p.set(currents[idx])

    def get_devices(self) -> list[DeviceAccess]:
        return self.__devices

    def set_magnet_rigidity(self, brho: np.double):
        pass

    def has_physics(self) -> bool:
        return self._cfg.physics is not None

    def has_hardware(self) -> bool:
        return self._cfg.powerconverters is not None

    def __repr__(self):
        return __pyaml_repr__(self)
