import numpy as np
from pydantic import BaseModel, ConfigDict

from ..common.element import __pyaml_repr__
from ..configuration.curve import Curve
from ..control.deviceaccess import DeviceAccess
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "LinearMagnetModel"


class ConfigModel(BaseModel):
    """
    Linear magnet model.

    Parameters
    ----------

    curve: Curve | None
        Curve object used for interpolation. By default,
        identity curve is used.
    powerconverter: DeviceAccess | None
        Power converter device to apply currrent
    calibration_factor: float = 1.0
        Correction factor applied to the curve
    calibration_offset: float = 0.0
        Correction offset applied to the curve
    crosstalk: float = 1.0
        Crosstalk factor
    unit: str
        Unit of the strength (i.e. 1/m or m-1)

    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    curve: Curve | None = None
    powerconverter: DeviceAccess | None
    calibration_factor: float = 1.0
    calibration_offset: float = 0.0
    crosstalk: float = 1.0
    unit: str


class LinearMagnetModel(MagnetModel):
    """
    Class that handle manget current/strength conversion using
    linear interpolation for a single function magnet
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        if self._cfg.curve:
            self.__curve = cfg.curve.get_curve()
            self.__curve[:, 1] = (
                self.__curve[:, 1] * cfg.calibration_factor * cfg.crosstalk
                + cfg.calibration_offset
            )
            self.__rcurve = Curve.inverse(self.__curve)
        else:
            self.__curve = None
            self.__rcurve = None
            self.__g = cfg.calibration_factor * cfg.crosstalk
            self.__o = cfg.calibration_offset
        self.__strength_unit = cfg.unit
        self.__hardware_unit = cfg.powerconverter.unit()
        self.__brho = np.nan
        self.__ps = cfg.powerconverter

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        if self.__rcurve is not None:
            _current = np.interp(
                strengths[0] * self.__brho, self.__rcurve[:, 0], self.__rcurve[:, 1]
            )
        else:
            _current = (strengths[0] * self.__brho) / self.__g + self.__o
        return np.array([_current])

    def compute_strengths(self, currents: np.array) -> np.array:
        if self.__curve is not None:
            _strength = (
                np.interp(currents[0], self.__curve[:, 0], self.__curve[:, 1])
                / self.__brho
            )
        else:
            _strength = ((currents[0] - self.__o) * self.__g) / self.__brho
        return np.array([_strength])

    def get_strength_units(self) -> list[str]:
        return [self.__strength_unit] if self.__strength_unit is not None else [""]

    def get_hardware_units(self) -> list[str]:
        return [self.__hardware_unit] if self.__hardware_unit is not None else [""]

    def get_devices(self) -> list[DeviceAccess]:
        return [self.__ps]

    def set_magnet_rigidity(self, brho: np.double):
        self.__brho = brho

    def __repr__(self):
        return __pyaml_repr__(self)
