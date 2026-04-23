import numpy as np

# from ..common.element import __pyaml_repr__
from ..configuration.curve import Curve, CurveSchema
from ..control.deviceaccess import DeviceAccess, DeviceAccessSchema
from .model import MagnetModel, MagnetModelSchema


class LinearMagnetModelSchema(MagnetModelSchema):
    """
    Linear magnet model.

    Parameters
    ----------
    curve : Curve or None, optional
        Curve object used for interpolation. By default,
        identity curve is used.
    powerconverter : DeviceAccess or None, optional
        Power converter device to apply currrent
    calibration_factor : float, optional
        Correction factor applied to the curve. Default: 1.0
    calibration_offset : float, optional
        Correction offset applied to the curve. Default: 0.0
    crosstalk : float, optional
        Crosstalk factor. Default: 1.0
    unit : str
        Unit of the strength (i.e. 1/m or m-1)

    """

    curve: CurveSchema | None = None
    powerconverter: DeviceAccessSchema | None = None
    calibration_factor: float = 1.0
    calibration_offset: float = 0.0
    crosstalk: float = 1.0
    unit: str = ""


class LinearMagnetModel(MagnetModel):
    """
    Class that handle manget current/strength conversion using
    linear interpolation for a single function magnet
    """

    def __init__(
        self,
        curve: Curve | None = None,
        powerconverter: DeviceAccess | None = None,
        calibration_factor: float = 1.0,
        calibration_offset: float = 0.0,
        crosstalk: float = 1.0,
        unit: str = "",
    ):
        if curve:
            self.__curve = curve.get_curve()
            self.__curve[:, 1] = self.__curve[:, 1] * calibration_factor * crosstalk + calibration_offset
            self.__rcurve = Curve.inverse(self._curve)
        else:
            self.__curve = None
            self.__rcurve = None
            self.__g = calibration_factor * crosstalk
            self.__o = calibration_offset

        self.__strength_unit = unit
        if powerconverter:
            self.__hardware_unit = powerconverter.unit()
        self.__brho = np.nan
        self.__ps = powerconverter

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        if self.__rcurve is not None:
            _current = np.interp(strengths[0] * self.__brho, self.__rcurve[:, 0], self.__rcurve[:, 1])
        else:
            _current = (strengths[0] * self.__brho) / self.__g + self.__o
        return np.array([_current])

    def compute_strengths(self, currents: np.array) -> np.array:
        if self.__curve is not None:
            _strength = np.interp(currents[0], self.__curve[:, 0], self.__curve[:, 1]) / self.__brho
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


#    def __repr__(self):
#        return __pyaml_repr__(self)
