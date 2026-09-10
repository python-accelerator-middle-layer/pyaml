"""
Spline-based conversion model for calibrated magnets.

This model uses excitation-curve interpolation to convert between physical magnet strengths and hardware values.
"""

import numpy as np
from scipy.interpolate import make_smoothing_spline

from ..common.element import __pyaml_repr__
from ..validation import DynamicValidation, register_schema
from .curve import Curve
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "SplineMagnetModel"


@register_schema
class SplineMagnetModel(MagnetModel, DynamicValidation):
    """
    Magnet model that converts between strength and hardware current using
    spline interpolation.

    The model represents a single-function magnet and builds two smoothing
    splines from the supplied excitation curve:

    - a forward spline for converting hardware current to magnet strength
    - an inverse spline for converting magnet strength to hardware current

    The input curve is first scaled by ``calibration_factor`` and ``crosstalk``
    and shifted by ``calibration_offset`` before the splines are created.

    Parameters
    ----------
    curve : Curve
        Excitation curve used for interpolation.
    powerconverter : str | None, optional
        Name of the associated power converter device.
    calibration_factor : float, optional
        Multiplicative correction applied to the curve. Default is ``1.0``.
    calibration_offset : float, optional
        Additive correction applied to the curve. Default is ``0.0``.
    crosstalk : float, optional
        Crosstalk factor applied to the curve. Default is ``1.0``.
    unit : str | None, optional
        Strength unit, such as ``m-1`` or ``m-2``.
    hardware_unit : str | None, optional
        Hardware unit, such as ``A`` or ``V``.
    alpha : float, optional
        Smoothing parameter passed to :func:`scipy.interpolate.make_smoothing_spline`.
        ``alpha = 0`` gives exact interpolation through the data points.

    Methods
    -------
    compute_hardware_values(strengths)
        Convert magnet strengths to hardware values.
    compute_strengths(currents)
        Convert hardware values to magnet strengths.
    get_strength_units()
        Return the units of magnet strengths.
    get_hardware_units()
        Return the units of hardware values.
    get_device_names()
        Return the associated device names.
    set_magnet_rigidity(brho)
        Set the magnetic rigidity used for conversion.

    Notes
    -----
    The magnet rigidity ``brho`` must be set with :meth:`set_magnet_rigidity`
    before using the conversion methods.
    """

    def __init__(
        self,
        curve: Curve,
        powerconverter: str | None = None,
        calibration_factor: float = 1.0,
        calibration_offset: float = 0.0,
        crosstalk: float = 1.0,
        unit: str | None = None,
        hardware_unit: str | None = None,
        alpha: float = 0.0,
    ):
        """
        Initialize the SplineMagnetModel.
        """
        self.__curve = curve.get_curve()
        self.__curve[:, 1] = self.__curve[:, 1] * calibration_factor * crosstalk + calibration_offset
        rcurve = Curve.inverse(self.__curve)
        self.__strength_unit = unit
        self.__hardware_unit = hardware_unit
        self.__brho = np.nan
        self.__ps = powerconverter
        self.__spl = make_smoothing_spline(self.__curve[:, 0], self.__curve[:, 1], lam=alpha)
        self.__rspl = make_smoothing_spline(rcurve[:, 0], rcurve[:, 1], lam=alpha)

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        """
        Convert magnet strengths to hardware values.

        Parameters
        ----------
        strengths : np.array
            Magnet strengths to convert, in the unit reported by :meth:`get_strength_unit`.

        Returns
        -------
        np.array
            Hardware values corresponding to ``strengths``.
        """
        _current = self.__rspl(strengths[0] * self.__brho)
        return np.array([_current])

    def compute_strengths(self, currents: np.array) -> np.array:
        """
        Convert hardware values to magnet strengths.

        Parameters
        ----------
        currents : np.array
            Hardware values to convert, in the unit reported by :meth:`get_hardware_unit`.

        Returns
        -------
        np.array
            Strengths corresponding to ``currents``.
        """
        _strength = self.__spl(currents[0]) / self.__brho
        return np.array([_strength])

    def get_strength_units(self) -> list[str]:
        """Return the units of magnet strengths."""
        return [self.__strength_unit] if self.__strength_unit is not None else [""]

    def get_hardware_units(self) -> list[str]:
        """Return the units of hardware values."""
        return [self.__hardware_unit] if self.__hardware_unit is not None else [""]

    def get_device_names(self) -> list[str | None]:
        """Return the associated device names."""
        return [self.__ps]

    def set_magnet_rigidity(self, brho: np.double):
        """
        Set the magnetic rigidity used for conversion.

        Parameters
        ----------
        brho : np.double
            Magnetic rigidity in tesla metres, used to scale strengths into hardware values.
        """
        self.__brho = brho

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
