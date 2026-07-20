import numpy as np

from ..common.element import __pyaml_repr__
from ..validation import DynamicValidation, register_schema
from .curve import Curve
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "LinearMagnetModel"


@register_schema
class LinearMagnetModel(MagnetModel, DynamicValidation):
    """
    Linear magnet model for a single magnet function.

    This model converts between magnet strengths and hardware currents using a
    single excitation curve or, if no curve is provided, a linear scaling with an
    optional offset. It is intended for single-function magnets such as correctors
    or other elements that use one current channel.

    Parameters
    ----------
    unit : str
        Unit of the magnet strength, for example ``"1/m"`` or ``"m-1"``.
    hardware_unit : str
        Unit of the hardware value, for example ``"A"`` or ``"V"``.
    curve : Curve | None, optional
        Excitation curve used for interpolation. If omitted, a linear conversion
        is used instead.
    powerconverter : str | None, optional
        Name of the power converter device used to apply current.
    calibration_factor : float, optional
        Multiplicative correction applied to the curve or linear scaling.
        Default is ``1.0``.
    calibration_offset : float, optional
        Additive correction applied to the curve or linear scaling.
        Default is ``0.0``.
    crosstalk : float, optional
        Crosstalk factor applied together with the calibration factor.
        Default is ``1.0``.

    Notes
    -----
    If a curve is provided, the model interpolates between strength and current
    values using the curve and its inverse. If no curve is provided, the model
    uses a simple linear relation with the stored scaling factor and offset.
    """

    def __init__(
        self,
        unit: str,
        hardware_unit: str,
        curve: Curve | None = None,
        powerconverter: str | None = None,
        calibration_factor: float = 1.0,
        calibration_offset: float = 0.0,
        crosstalk: float = 1.0,
    ):
        if curve:
            self.__curve = curve.get_curve()
            self.__curve[:, 1] = self.__curve[:, 1] * calibration_factor * crosstalk + calibration_offset
            self.__rcurve = Curve.inverse(self.__curve)
        else:
            self.__curve = None
            self.__rcurve = None
            self.__g = calibration_factor * crosstalk
            self.__o = calibration_offset
        self.__strength_unit = unit
        self.__hardware_unit = hardware_unit
        self.__ps = powerconverter
        self.__brho = np.nan

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

    def get_device_names(self) -> list[str | None]:
        return [self.__ps]

    def set_magnet_rigidity(self, brho: np.double):
        self.__brho = brho

    def __repr__(self):
        return __pyaml_repr__(self)
