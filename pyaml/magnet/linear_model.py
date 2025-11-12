from .model import MagnetModel
from ..configuration.curve import Curve
from ..control.deviceaccess import DeviceAccess
from ..common.element import __pyaml_repr__

import numpy as np
from pydantic import BaseModel,ConfigDict

# Define the main class name for this module
PYAMLCLASS = "LinearMagnetModel"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    curve: Curve
    """Curve object used for interpolation"""
    powerconverter: DeviceAccess
    """Power converter device to apply currrent"""
    calibration_factor: float = 1.0
    """Correction factor applied to the curve"""
    calibration_offset: float = 0.0
    """Correction offset applied to the curve")"""
    crosstalk: float = 1.0
    """Crosstalk factor"""
    unit: str
    """Unit of the strength (i.e. 1/m or m-1)"""

class LinearMagnetModel(MagnetModel):
    """
    Class that handle manget current/strength conversion using linear interpolation for a single function magnet
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self.__curve = cfg.curve.get_curve()
        self.__curve[:, 1] = (
            self.__curve[:, 1] * cfg.calibration_factor * cfg.crosstalk + cfg.calibration_offset
        )
        self.__rcurve = Curve.inverse(self.__curve)
        self.__strength_unit = cfg.unit
        self.__hardware_unit = cfg.powerconverter.unit()
        self.__brho = np.nan
        self.__ps = cfg.powerconverter

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        _current = np.interp(
            strengths[0] * self.__brho, self.__rcurve[:, 0], self.__rcurve[:, 1]
        )
        return np.array([_current])

    def compute_strengths(self, currents: np.array) -> np.array:
        _strength = (
            np.interp(currents[0], self.__curve[:, 0], self.__curve[:, 1]) / self.__brho
        )
        return np.array([_strength])

    def get_strength_units(self) -> list[str]:
        return [self.__strength_unit] if self.__strength_unit is not None else [""]

    def get_hardware_units(self) -> list[str]:
        return [self.__hardware_unit] if self.__hardware_unit is not None else [""]

    def read_hardware_values(self) -> np.array:
        return [self.__ps.get()]

    def readback_hardware_values(self) -> np.array:
        return [self.__ps.readback()]

    def send_hardware_values(self, currents: np.array):
        self.__ps.set(currents[0])

    def get_devices(self) -> list[DeviceAccess]:
        return [self.__ps]

    def set_magnet_rigidity(self, brho: np.double):
        self.__brho = brho

    def __repr__(self):
        return __pyaml_repr__(self)

    