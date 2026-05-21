import numpy as np
from pydantic import BaseModel, ConfigDict
from scipy.interpolate import make_smoothing_spline

from ..common.element import __pyaml_repr__
from ..configuration import ConfigurationSchema, register_schema
from ..configuration.curve import Curve, CurveSchema
from ..control.deviceaccess import DeviceAccess, DeviceAccessSchema
from .model import MagnetModel


class SplineMagnetModelSchema(ConfigurationSchema):
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

    model_config = ConfigDict(extra="forbid")

    curve: CurveSchema
    powerconverter: DeviceAccessSchema | None
    calibration_factor: float = 1.0
    calibration_offset: float = 0.0
    crosstalk: float = 1.0
    unit: str
    alpha: float = 0.0


@register_schema(SplineMagnetModelSchema)
class SplineMagnetModel(MagnetModel):
    """
    Class that handle manget current/strength conversion using
    spline interpolation for a single function magnet
    """

    def __init__(
        self,
        curve: Curve,
        unit: str,
        powerconverter: DeviceAccessSchema | None,
        calibration_factor: float = 1.0,
        calibration_offset: float = 0.0,
        crosstalk: float = 1.0,
        alpha: float = 0.0,
    ):
        self.__curve = curve.get_curve()
        self.__curve[:, 1] = self.__curve[:, 1] * calibration_factor * crosstalk + calibration_offset
        rcurve = Curve.inverse(self.__curve)
        self.__strength_unit = unit
        self.__hardware_unit = powerconverter.unit()
        self.__brho = np.nan
        self.__ps = powerconverter
        self.__spl = make_smoothing_spline(self.__curve[:, 0], self.__curve[:, 1], lam=alpha)
        self.__rspl = make_smoothing_spline(rcurve[:, 0], rcurve[:, 1], lam=alpha)

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
