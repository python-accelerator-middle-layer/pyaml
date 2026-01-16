import numpy as np
from pydantic import BaseModel, ConfigDict
from scipy.interpolate import make_smoothing_spline

from ..common.element import __pyaml_repr__
from ..configuration.curve import Curve
from ..control.deviceaccess import DeviceAccess
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "SplineMagnetModel"


class ConfigModel(BaseModel):
    """
    Configuration model for spline magnet model

    Parameters
    ----------
    curve : Curve
        Curve object used for interpolation
    powerconverter : DeviceAccess, optional
        Power converter device to apply current
    calibration_factor : float, optional
        Correction factor applied to the curve. Default: 1.0
    calibration_offset : float, optional
        Correction offset applied to the curve. Default: 0.0
    crosstalk : float, optional
        Crosstalk factor. Default: 1.0
    unit : str
        Unit of the strength (i.e. 1/m or m-1)
    alpha : float, optional
        Regularization parameter (alpha >= 0). alpha = 0 means the interpolation
        passes through all the points of the curve. Default: 0.0
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    curve: Curve
    powerconverter: DeviceAccess | None
    calibration_factor: float = 1.0
    calibration_offset: float = 0.0
    crosstalk: float = 1.0
    unit: str
    alpha: float = 0.0


class SplineMagnetModel(MagnetModel):
    """
    Class that handle manget current/strength conversion using
    spline interpolation for a single function magnet
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self.__curve = cfg.curve.get_curve()
        self.__curve[:, 1] = (
            self.__curve[:, 1] * cfg.calibration_factor * cfg.crosstalk
            + cfg.calibration_offset
        )
        rcurve = Curve.inverse(self.__curve)
        self.__strength_unit = cfg.unit
        self.__hardware_unit = cfg.powerconverter.unit()
        self.__brho = np.nan
        self.__ps = cfg.powerconverter
        self.__spl = make_smoothing_spline(
            self.__curve[:, 0], self.__curve[:, 1], lam=cfg.alpha
        )
        self.__rspl = make_smoothing_spline(rcurve[:, 0], rcurve[:, 1], lam=cfg.alpha)

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        _current = self.__rspl(strengths[0] * self.__brho)
        return np.array([_current])

    def compute_strengths(self, currents: np.array) -> np.array:
        _strength = self.__spl(currents[0]) / self.__brho
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
