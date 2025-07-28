import numpy as np
from pydantic import BaseModel
from scipy.interpolate import make_smoothing_spline

from .model import MagnetModel
from ..configuration.curve import Curve
from ..control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "SplineMagnetModel"

class ConfigModel(BaseModel):

    curve: Curve
    """Curve object used for interpolation"""
    powerconverter: DeviceAccess
    """Power converter device to apply currrent"""
    calibration_factor: float = 1.0
    """Correction factor applied to the curve"""
    calibration_offset: float = 0.0
    """Correction offset applied to the curve"""
    unit: str
    """Unit of the strength (i.e. 1/m or m-1)"""
    alpha: float = 0.0
    """Regularization parameter (alpha>=0), aplha=0 the interpolation pass through all the points of the curve"""

class SplineMagnetModel(MagnetModel):
    """
    Class that handle manget current/strength conversion using spline interpolation for a single function magnet
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self._curve = cfg.curve.get_curve()
        self._curve[:, 1] = (
            self._curve[:, 1] * cfg.calibration_factor + cfg.calibration_offset
        )
        self._strength_unit = cfg.unit
        self._current_unit = cfg.powerconverter.unit()
        self._brho = np.nan
        self._ps = cfg.powerconverter
        self._spl = make_smoothing_spline(self._curve[:, 0], self._curve[:, 1], lam=cfg.alpha)
        self._rspl = make_smoothing_spline(self._curve[:, 1], self._curve[:, 0], lam=cfg.alpha)

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        _current = self._rspl(strengths[0] * self._brho)
        return np.array([_current])

    def compute_strengths(self, currents: np.array) -> np.array:
        _strength = self._spl(currents[0]) / self._brho
        return np.array([_strength])

    def get_strength_units(self) -> list[str]:
        return [self._strength_unit] if self._strength_unit is not None else [""]

    def get_hardware_units(self) -> list[str]:
        return [self._current_unit] if self._current_unit is not None else [""]

    def read_hardware_values(self) -> np.array:
        return [self._ps.get()]

    def readback_hardware_values(self) -> np.array:
        return [self._ps.readback()]

    def send_harware_values(self, currents: np.array):
        self._ps.set(currents[0])

    def set_magnet_rigidity(self, brho: np.double):
        self._brho = brho

    def __repr__(self):
        return "%s(curve[%d], unit=%s)" % (
            self.__class__.__name__,
            len(self._curve),
            self._strength_unit,
        )
