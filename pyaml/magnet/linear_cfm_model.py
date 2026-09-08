"""
Linear conversion model for combined-function magnets.

This model converts multiple multipole strengths to hardware values using per-function linear calibration parameters.
"""

import numpy as np

from ..common.element import __pyaml_repr__
from ..common.exception import PyAMLException
from ..validation import DynamicValidation, register_schema
from .curve import Curve
from .matrix import Matrix
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "LinearCFMagnetModel"


@register_schema
class LinearCFMagnetModel(MagnetModel, DynamicValidation):
    """
    Linear combined-function magnet model.

    This model converts between magnet strengths and hardware currents using
    precomputed excitation curves, optional calibration and pseudo-current
    corrections, and an optional coupling matrix to separate or combine multipole
    responses. It is intended for combined-function magnets where several
    multipoles share a common hardware representation.

    Parameters

    multipoles : list[str]
    Names of the supported multipoles, for example ["B0", "A1", "B2"].
    curves : list[Curve]
    Excitation curves, one per multipole.
    powerconverters : list[str | None]
    Names of the power converter devices associated with the hardware currents.
    hardware_units : list[str]
    Units of the hardware variables, one per power converter.
    calibration_factors : list[float] | None, optional
    Multiplicative correction factors applied to the excitation curves.
    Defaults to ones.
    calibration_offsets : list[float] | None, optional
    Additive correction offsets applied to the excitation curves.
    Defaults to zeros.
    pseudo_factors : list[float] | None, optional
    Multiplicative factors applied to pseudo currents.
    Defaults to ones.
    pseudo_offsets : list[float] | None, optional
    Additive offsets applied to pseudo currents.
    Defaults to zeros.
    matrix : Matrix | None, optional
    Coupling matrix mapping power-supply currents to pseudo currents.
    Defaults to the identity matrix.
    units : list[str] | None, optional
    Strength units, one per multipole.

    Raises

    PyAMLException
    If the list lengths do not match, if the matrix has the wrong shape, or
    if the configuration is otherwise inconsistent.

    Parameters
    ----------
    multipoles : list[str]
        Names of the supported multipoles, for example ["B0", "A1", "B2"].
    curves : list[Curve]
        Excitation curves, one per multipole.
    powerconverters : list[str | None]
        Names of the power converter devices associated with the hardware currents.
    hardware_units : list[str]
        Units of the hardware variables, one per power converter.
    calibration_factors : list[float] | None
        Multiplicative correction factors applied to the excitation curves. Defaults to ones.
    calibration_offsets : list[float] | None
        Additive correction offsets applied to the excitation curves. Defaults to zeros.
    pseudo_factors : list[float] | None
        Multiplicative factors applied to pseudo currents. Defaults to ones.
    pseudo_offsets : list[float] | None
        Additive offsets applied to pseudo currents. Defaults to zeros.
    matrix : Matrix | None
        Coupling matrix mapping power-supply currents to pseudo currents. Defaults to the identity matrix.
    units : list[str] | None
        Strength units, one per multipole.

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
    has_hardware()
        Return whether the model provides hardware values.
    """

    def __init__(
        self,
        multipoles: list[str],
        curves: list[Curve],
        powerconverters: list[str | None],
        hardware_units: list[str],
        calibration_factors: list[float] | None = None,
        calibration_offsets: list[float] | None = None,
        pseudo_factors: list[float] | None = None,
        pseudo_offsets: list[float] | None = None,
        matrix: Matrix | None = None,
        units: list[str] | None = None,
    ):
        """
        Initialize the LinearCFMagnetModel.
        """
        self.multipoles = multipoles
        self._curves = curves
        self._powerconverters = powerconverters
        self.hardware_units = hardware_units
        self._calibration_factors = calibration_factors
        self._calibration_offsets = calibration_offsets
        self._pseudo_factors = pseudo_factors
        self._pseudo_offsets = pseudo_offsets
        self._matrix = matrix
        self.units = units
        self._brho = np.nan

        # Check config
        self.__nbFunction: int = len(self.multipoles)
        self.__nbPS: int = len(self._powerconverters)

        if self._calibration_factors is None:
            self.__calibration_factors = np.ones(self.__nbFunction)
        else:
            self.__calibration_factors = self._calibration_factors

        if self._calibration_offsets is None:
            self.__calibration_offsets = np.zeros(self.__nbFunction)
        else:
            self.__calibration_offsets = self._calibration_offsets

        if self._pseudo_factors is None:
            self.__pf = np.ones(self.__nbFunction)
        else:
            self.__pf = self._pseudo_factors

        if self._pseudo_offsets is None:
            self.__po = np.zeros(self.__nbFunction)
        else:
            self.__po = self._pseudo_factors

        self.__check_len(self.__calibration_factors, "calibration_factors", self.__nbFunction)
        self.__check_len(self.__calibration_offsets, "calibration_offsets", self.__nbFunction)
        self.__check_len(self.__pf, "pseudo_factors", self.__nbFunction)
        self.__check_len(self.__po, "pseudo_offsets", self.__nbFunction)
        self.__check_len(self.units, "units", self.__nbFunction)
        self.__check_len(self.hardware_units, "hardware_units", self.__nbPS)
        self.__check_len(self._curves, "curves", self.__nbFunction)

        if self._matrix is None:
            self.__matrix = np.identity(self.__nbFunction)
        else:
            self.__matrix = self._matrix.get_matrix()

        _s = np.shape(self.__matrix)

        if len(_s) != 2 or _s[0] != self.__nbFunction or _s[1] != self.__nbPS:
            raise PyAMLException(
                f"matrix wrong dimension ({self.__nbFunction}x{self.__nbPS} expected but got {_s[0]}x{_s[1]})"
            )

        self.__curves = []
        self.__rcurves = []

        # Apply factor and offset
        for idx, c in enumerate(self._curves):
            self.__curves.append(c.get_curve())
            self.__curves[idx][:, 1] *= self.__calibration_factors[idx]
            self.__curves[idx][:, 1] += self.__calibration_offsets[idx]
            self.__rcurves.append(Curve.inverse(self.__curves[idx]))

        # Compute pseudo inverse
        self.__inv = np.linalg.pinv(self.__matrix)

    def __check_len(self, obj, name, expected_len):
        """
        Validate the length of a model configuration sequence.

        Parameters
        ----------
        obj : object
            Sequence whose length should be checked.
        name : object
            Configuration-field name used in an error message.
        expected_len : object
            Required number of entries.

        Raises
        ------
        PyAMLException
            If ``obj`` does not contain ``expected_len`` entries.
        """
        lgth = len(obj)
        if lgth != expected_len:
            raise PyAMLException(
                f"{name} does not have the expected number of items ({expected_len} items expected but got {lgth})"
            )

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        """
        Convert magnet strengths to hardware values.

        Parameters
        ----------
        strengths : np.array
            Strength of each magnet function, ordered as declared by the model.

        Returns
        -------
        np.array
            Hardware value of each power converter, ordered as declared by the model.
        """
        _pI = np.zeros(self.__nbFunction)
        for idx, c in enumerate(self.__rcurves):
            _pI[idx] = self.__pf[idx] * np.interp(strengths[idx] * self._brho, c[:, 0], c[:, 1]) + self.__po[idx]
        _currents = np.matmul(self.__inv, _pI)
        return _currents

    def compute_strengths(self, currents: np.array) -> np.array:
        """
        Convert hardware values to magnet strengths.

        Parameters
        ----------
        currents : np.array
            Hardware value of each power converter, ordered as declared by the model.

        Returns
        -------
        np.array
            Strength of each magnet function, ordered as declared by the model.
        """
        _strength = np.zeros(self.__nbFunction)
        _pI = np.matmul(self.__matrix, currents)
        for idx, c in enumerate(self.__curves):
            _strength[idx] = np.interp((_pI[idx] - self.__po[idx]) / self.__pf[idx], c[:, 0], c[:, 1]) / self._brho
        return _strength

    def get_strength_units(self) -> list[str]:
        """Return the units of magnet strengths."""
        return self.units

    def get_hardware_units(self) -> list[str]:
        """Return the units of hardware values."""
        return self.hardware_units

    def get_device_names(self) -> list[str | None]:
        """Return the associated device names."""
        return self._powerconverters

    def set_magnet_rigidity(self, brho: np.double):
        """
        Set the magnetic rigidity used for conversion.

        Parameters
        ----------
        brho : np.double
            Magnetic rigidity in tesla metres, used to scale strengths into hardware values.
        """
        self._brho = brho

    def has_hardware(self) -> bool:
        """Return whether the model provides hardware values."""
        return (self.__nbPS == self.__nbFunction) and np.allclose(self.__matrix, np.eye(self.__nbFunction))

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
