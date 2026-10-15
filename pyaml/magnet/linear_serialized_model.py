"""
Linear conversion model for serialized magnets.

This model applies linear calibration to a configurable sequence of serialized magnet elements and hardware channels.
"""

import logging

import numpy as np

from ..common.element import __pyaml_repr__
from ..common.exception import PyAMLException
from ..validation import DynamicValidation, register_schema
from .curve import Curve
from .inline_curve import InlineCurve
from .linear_model import LinearMagnetModel
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "LinearSerializedMagnetModel"

logger = logging.getLogger(__name__)

# Relative gap above which strengths requested for a series are considered unreachable with a single hardware value
_SPREAD_RTOL = 1e-6


def _get_length(elem) -> int:
    """
    Return the number of serialized entries represented by a value.

    ``None`` represents no entries, a list represents one entry per item, and
    any other value represents a single entry.

    Parameters
    ----------
    elem : object
        Configuration value to inspect.

    Returns
    -------
    int
        Number of serialized entries represented by ``elem``.
    """
    if elem is None:
        return 0
    if isinstance(elem, list):
        return len(elem)
    else:
        return 1


def _get_max_length(*args, **kwargs) -> int:
    """
    Return the largest serialized-entry count among the inputs.

    Each positional and keyword value is measured with :func:`_get_length`.
    This is used to determine the sequence length needed when scalar and list
    configuration values are supplied together.

    Parameters
    ----------
    *args : object
        Positional configuration values.
    **kwargs : object
        Keyword configuration values.

    Returns
    -------
    int
        Largest represented entry count, or ``0`` when no values are given.
    """
    max_args = max([_get_length(elem) for elem in args]) if args else 0
    max_kwargs = max([_get_length(elem) for elem in kwargs.values()]) if kwargs else 0
    return max(max_args, max_kwargs)


def _to_list_of_length(elem, length: int) -> list:
    """
    Expand a scalar configuration value to a list of the requested length.

    Parameters
    ----------
    elem : object
        Scalar or list configuration value.
    length : int
        Required list length when ``elem`` is scalar.

    Returns
    -------
    list
        The original list, or a list repeating ``elem`` ``length`` times.
    """
    if isinstance(elem, list):
        return elem
    else:
        return [elem] * length


def _check_len(obj, name, expected_length):
    """
    Validate the length of a serialized-magnet configuration sequence.

    Parameters
    ----------
    obj : object
        Sequence whose length should be checked.
    name : object
        Configuration-field name used in an error message.
    expected_length : object
        Required number of entries.

    Raises
    ------
    PyAMLException
        If ``obj`` does not contain ``expected_length`` entries.
    """
    length = len(obj)
    if length != expected_length:
        raise PyAMLException(
            f"{name} does not have the expected number of items ({expected_length} items expected but got {length})"
        )


@register_schema
class LinearSerializedMagnetModel(MagnetModel, DynamicValidation):
    """
    Linear model for a serialized combined-function magnet.

    This model wraps one or more :class:`LinearMagnetModel` instances and
    represents a combined-function magnet as a set of sub-models that share a
    common hardware readout. The excitation curve may be provided either as a
    single :class:`Curve` instance, which is replicated for all magnets, or as a
    list of curves with one entry per magnet.

    The model supports per-magnet calibration factors, calibration offsets, and
    crosstalk values. Strengths are converted to a single hardware current by
    evaluating the individual sub-models and averaging their corresponding
    hardware values. Conversely, a hardware current is mapped back to a
    strength value for each sub-model.

    The serialized magnets have a single degree of freedom, the power-supply
    current ``I``. Magnet ``i`` has the strength ``k_i = f_i(I)``, where ``f_i``
    is its sub-model. The family strength is the average strength
    ``sum(f_i(I)) / N``.

    Parameters
    ----------
    curves : Curve or list[Curve]
        Excitation curve(s) used by the magnet model. A single curve is reused
        for all magnets, while a list must contain one curve per magnet.
    calibration_factors : float or list[float], optional
        Multiplicative correction factor applied to each curve.
        If omitted, defaults to 1.0 for all magnets.
    calibration_offsets : float or list[float], optional
        Additive correction offset applied to each curve.
        If omitted, defaults to 0.0 for all magnets.
    crosstalk : float or list[float], optional
        Crosstalk factor for each magnet. If omitted, defaults to 1.0.
    powerconverter : str, optional
        Name of the associated power converter or power converter group.
    unit : str, optional
        Strength unit, such as ``rad``, ``m-1`` or ``m-2``.
    hardware_unit : str, optional
        Hardware unit, typically ``A`` or ``V``.

    Methods
    -------
    set_number_of_magnets(nb_magnets)
        Set the number of serialized magnets and rebuild submodels.
    get_sub_model(index)
        Return the linear submodel for one serialized magnet.
    compute_hardware_values(strengths)
        Convert magnet strengths to hardware values.
    compute_strengths(currents)
        Convert hardware values to magnet strengths.
    compute_hardware_values_partial(current_hardware, strengths_by_index)
        Convert the strengths of some magnets of the series to the shared hardware value.
    compute_mean_strength(current)
        Return the average strength of the series for a hardware value.
    compute_hardware_from_mean_strength(strength)
        Return the hardware value giving an average strength of the series.
    compute_hardware_from_strengths(strengths)
        Return the hardware value for a requested strength of each magnet of the series.
    shares_power_supply()
        Return True, all the magnets of the series share one power supply.
    get_strength_units()
        Return the units of magnet strengths.
    get_hardware_units()
        Return the units of hardware values.
    get_device_names()
        Return the associated device names.
    set_magnet_rigidity(brho)
        Set the magnetic rigidity used for conversion.
    get_magnet_rigidity()
        Return the configured magnetic rigidity.

    Notes
    -----
    The number of magnets is inferred from the longest list among the supplied
    configuration values. Scalars are expanded to match that length.

    Configuration
    -------------
    .. code-block:: yaml

        type: pyaml.magnet.linear_serialized_model
        unit: 1/m
        hardware_unit: A
        calibration_factors: 1.0
        calibration_offsets: 0.0
        curves:
          type: pyaml.magnet.csvcurve
          file: path/to/excitation_curve.csv
        powerconverter: DEVICE/POWER_CONVERTER_CURRENT
    """

    def __init__(
        self,
        curves: Curve | list[Curve],
        calibration_factors: float | list[float] | None = None,
        calibration_offsets: float | list[float] | None = None,
        crosstalk: float | list[float] = 1.0,
        powerconverter: str | None = None,
        unit: str | None = None,
        hardware_unit: str | None = None,
    ):
        """
        Initialize a linear model for serialized magnets.
        """
        self.__brho = np.nan
        self._curves = curves
        self._calibration_factors = calibration_factors
        self._calibration_offsets = calibration_offsets
        self._crosstalk = crosstalk
        self._powerconverter = powerconverter
        self._unit = unit
        self._hardware_unit = hardware_unit

        # Check config
        self.__nbMagnets: int = _get_max_length(curves, calibration_factors, calibration_offsets, crosstalk)
        self.__calibration_factors = np.ones(self.__nbMagnets)
        self.__calibration_offsets = np.ones(self.__nbMagnets)
        self.__crosstalk = np.ones(self.__nbMagnets)
        self.__curves = _to_list_of_length(curves, self.__nbMagnets)
        self.__sub_models: list[LinearMagnetModel] = []

    def __initialize(self):
        """
        Normalize serialized-magnet calibration and build submodels.

        Scalar calibration values are expanded to the configured number of
        magnets, sequence lengths are validated, and one
        :class:`LinearMagnetModel` is created for each serialized element.
        """
        if self._calibration_factors is None:
            self.__calibration_factors = np.ones(self.__nbMagnets)
        else:
            self.__calibration_factors = _to_list_of_length(self._calibration_factors, self.__nbMagnets)

        if self._calibration_offsets is None:
            self.__calibration_offsets = np.zeros(self.__nbMagnets)
        else:
            self.__calibration_offsets = _to_list_of_length(self._calibration_offsets, self.__nbMagnets)

        if self._crosstalk is None:
            self.__crosstalk = np.zeros(self.__nbMagnets)
        else:
            self.__crosstalk = _to_list_of_length(self._crosstalk, self.__nbMagnets)
        self.__curves = _to_list_of_length(self._curves, self.__nbMagnets)
        if isinstance(self._curves, list):
            self.__curves = self._curves
        else:
            self.__curves: list[Curve] = []
            for _ in range(self.__nbMagnets):
                curve = InlineCurve(mat=self._curves.get_curve())
                self.__curves.append(curve)

        _check_len(self.__calibration_factors, "calibration_factors", self.__nbMagnets)
        _check_len(self.__calibration_offsets, "calibration_offsets", self.__nbMagnets)
        _check_len(self.__crosstalk, "crosstalk", self.__nbMagnets)
        _check_len(self.__curves, "curves", self.__nbMagnets)

        self.__sub_models: list[LinearMagnetModel] = []
        for magnet_idx in range(self.__nbMagnets):
            sub_model = dict(
                curve=self.__curves[magnet_idx],
                calibration_factor=self.__calibration_factors[magnet_idx],
                calibration_offset=self.__calibration_offsets[magnet_idx],
                crosstalk=self.__crosstalk[magnet_idx],
                powerconverter=self._powerconverter,
                unit=self._unit,
                hardware_unit=self._hardware_unit,
            )
            self.__sub_models.append(LinearMagnetModel(**sub_model))

    def set_number_of_magnets(self, nb_magnets: int):
        """
        Set the number of serialized magnets and rebuild submodels.

        Parameters
        ----------
        nb_magnets : int
            Number of serialized magnets represented by the model.
        """
        self.__nbMagnets = nb_magnets
        self.__initialize()

    def get_sub_model(self, index: int) -> LinearMagnetModel:
        """
        Return the linear submodel for one serialized magnet.

        Parameters
        ----------
        index : int
            Zero-based serialized-magnet index.

        Returns
        -------
        LinearMagnetModel
            Linear conversion model for the selected magnet.
        """
        return self.__sub_models[index]

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        """
        Convert magnet strengths to hardware values.

        Parameters
        ----------
        strengths : np.array
            Physical strengths, one per serialized magnet.

        Returns
        -------
        np.array
            Hardware value obtained from the submodels: the mean of the hardware values implied by each strength.
        """
        currents = [model.compute_hardware_values([s])[0] for s, model in zip(strengths, self.__sub_models, strict=True)]
        return np.array([np.mean(currents)])

    def compute_strengths(self, currents: np.array) -> np.array:
        """
        Convert hardware values to magnet strengths.

        Parameters
        ----------
        currents : np.array
            Hardware value shared by the serialized magnets.

        Returns
        -------
        np.array
            Physical strength calculated for each serialized magnet.
        """
        current = currents[0]
        return np.array([model.compute_strengths([current])[0] for model in self.__sub_models])

    def compute_hardware_values_partial(
        self, current_hardware: np.ndarray, strengths_by_index: dict[int, float]
    ) -> np.ndarray:
        """
        Convert the strengths of some magnets of the series to the shared hardware value.

        The magnets that are not requested keep the strength given by the current hardware value. The completed
        strengths are then converted by :meth:`compute_hardware_from_strengths`, which logs a warning when they
        cannot all be reached with a single hardware value.

        Parameters
        ----------
        current_hardware : np.array
            Current hardware value of the series, one value per power supply.
        strengths_by_index : dict[int, float]
            Requested strengths, indexed by the position of the magnet in the series.

        Returns
        -------
        np.array
            Hardware value of the power supply, with the shape of ``current_hardware``.

        Raises
        ------
        PyAMLException
            If ``current_hardware`` does not hold one value per power supply of the series.
        """
        _check_len(current_hardware, "current_hardware", len(self.get_device_names()))
        strengths = self.compute_strengths(current_hardware)
        for idx, strength in strengths_by_index.items():
            strengths[idx] = strength
        return np.array([self.compute_hardware_from_strengths(strengths)])

    def compute_mean_strength(self, current: float) -> float:
        """
        Return the average strength of the series for a hardware value.

        Parameters
        ----------
        current : float
            Hardware value shared by the serialized magnets.

        Returns
        -------
        float
            Average strength ``sum(f_i(I)) / N``.
        """
        return float(np.mean(self.compute_strengths([current])))

    def compute_hardware_from_mean_strength(self, strength: float) -> float:
        """
        Return the hardware value giving an average strength of the series.

        The submodels are piecewise linear in the hardware value, so the average strength is piecewise linear on the
        union of the curve breakpoints and is inverted exactly by interpolation.

        Parameters
        ----------
        strength : float
            Requested average strength of the series.

        Returns
        -------
        float
            Hardware value ``I`` such that ``sum(f_i(I)) / N == strength``.

        Raises
        ------
        PyAMLException
            If the average strength is not monotonic in the hardware value.
        """
        currents = np.unique(np.concatenate([curve.get_curve()[:, 0] for curve in self.__curves]))
        strengths = np.array([self.compute_mean_strength(current) for current in currents])
        steps = np.diff(strengths)
        if np.all(steps <= 0):
            currents, strengths = currents[::-1], strengths[::-1]
        elif not np.all(steps >= 0):
            raise PyAMLException(
                f"Average strength of the series on {self._powerconverter} is not monotonic, it cannot be inverted"
            )
        return float(np.interp(strength, strengths, currents))

    def compute_hardware_from_strengths(self, strengths: np.ndarray) -> float:
        """
        Return the hardware value for a requested strength of each magnet of the series.

        The series has a single hardware value, so it solves ``sum(f_i(I)) == sum(k_i)`` for ``I``. When the requested
        strengths cannot all be reached with one hardware value, the result is a compromise and a warning is logged.

        Parameters
        ----------
        strengths : np.ndarray
            Requested strength ``k_i`` of each magnet of the series, in declaration order.

        Returns
        -------
        float
            Hardware value of the power supply.

        Raises
        ------
        PyAMLException
            If the number of strengths does not match the number of magnets, or if the average strength is not
            monotonic in the hardware value.
        """
        strengths = np.asarray(strengths, dtype=float)
        _check_len(strengths, "strengths", self.__nbMagnets)
        current = self.compute_hardware_from_mean_strength(float(np.mean(strengths)))
        gaps = self.compute_strengths([current]) - strengths
        if np.any(np.abs(gaps) > _SPREAD_RTOL * np.maximum(np.abs(strengths), 1.0)):
            worst = int(np.argmax(np.abs(gaps)))
            logger.warning(
                f"Inconsistent strengths requested for the series on {self._powerconverter}: the hardware value "
                f"{current} misses the requested strengths by up to {gaps[worst]:.3g} (magnet {worst})"
            )
        return current

    def shares_power_supply(self) -> bool:
        """Return True, all the magnets of the series share one power supply."""
        return True

    def get_strength_units(self) -> list[str]:
        """Return the units of magnet strengths."""
        return [self._unit] * self.__nbMagnets

    def get_hardware_units(self) -> list[str]:
        """Return the units of hardware values."""
        return [self._hardware_unit]

    def get_device_names(self) -> list[str | None]:
        """Return the associated device names."""
        return [self._powerconverter]

    def set_magnet_rigidity(self, brho: np.double):
        """
        Set the magnetic rigidity used for conversion.

        Parameters
        ----------
        brho : np.double
            Magnetic rigidity in tesla-metres used by the submodels.
        """
        self.__brho = brho
        [model.set_magnet_rigidity(brho) for model in self.__sub_models]

    def get_magnet_rigidity(self) -> np.double:
        """Return the configured magnetic rigidity."""
        return self.__brho

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
