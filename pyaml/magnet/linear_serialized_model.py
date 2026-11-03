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
# Normalized residual below which a breakpoint is considered to be exactly on the solution (rounding errors)
_ZERO_ATOL = 1e-12


def _first_zero(currents: np.ndarray, residuals: np.ndarray) -> float:
    """
    Return the lowest hardware value where an increasing piecewise-linear residual reaches zero.

    Parameters
    ----------
    currents : np.ndarray
        Breakpoints, in ascending order.
    residuals : np.ndarray
        Residual at each breakpoint, increasing.

    Returns
    -------
    float
        Hardware value, interpolated on the segment where the residual becomes non-negative.
    """
    above = np.nonzero(residuals >= 0.0)[0]
    if len(above) == 0:
        return float(currents[-1])
    j = above[0]
    if j == 0:
        return float(currents[0])
    return float(currents[j - 1] - residuals[j - 1] * (currents[j] - currents[j - 1]) / (residuals[j] - residuals[j - 1]))


def _last_zero(currents: np.ndarray, residuals: np.ndarray) -> float:
    """
    Return the highest hardware value where an increasing piecewise-linear residual is still zero.

    Parameters
    ----------
    currents : np.ndarray
        Breakpoints, in ascending order.
    residuals : np.ndarray
        Residual at each breakpoint, increasing.

    Returns
    -------
    float
        Hardware value, interpolated on the segment where the residual becomes positive.
    """
    below = np.nonzero(residuals <= 0.0)[0]
    if len(below) == 0:
        return float(currents[0])
    j = below[-1]
    if j == len(currents) - 1:
        return float(currents[-1])
    return float(currents[j] - residuals[j] * (currents[j + 1] - currents[j]) / (residuals[j + 1] - residuals[j]))


def _pick(low: float, high: float, current_hardware: float | None) -> float:
    """
    Return the hardware value chosen in the interval of solutions ``[low, high]``.

    Parameters
    ----------
    low : float
        Lowest hardware value of the solutions.
    high : float
        Highest hardware value of the solutions.
    current_hardware : float or None
        Present hardware value of the power supply, if known.

    Returns
    -------
    float
        ``current_hardware`` clipped to ``[low, high]``, so that the power supply does not move when it already gives
        the requested strengths, or the middle of the interval when the present hardware value is not known.
    """
    if current_hardware is None:
        return float((low + high) / 2.0)
    return float(np.clip(current_hardware, low, high))


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
    ``sum(p_i * f_i(I)) / N``, ``p_i`` being the declared polarity of magnet ``i``.
    The polarities must make every ``p_i * f_i`` vary in the same direction with
    ``I``: a series with magnets wired in reverse declares ``-1`` for them.

    The power supply only drives the series on the current range shared by all
    the excitation curves, ``[max_i I_min,i, min_i I_max,i]``. Hardware values
    computed from strengths are clamped to this range.

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
    polarities : int or list[int], optional
        Polarity ``p_i`` of each magnet in the family strength, ``+1`` or ``-1``.
        If omitted, defaults to ``+1`` for all magnets.
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
    compute_hardware_from_mean_strength(strength, current_hardware=None)
        Return the hardware value giving an average strength of the series.
    compute_hardware_from_strengths(strengths, current_hardware=None)
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

    Raises
    ------
    PyAMLException
        When the number of magnets is set, if a polarity is not ``+1`` or ``-1``,
        if the excitation curves share no current range, or if the polarities do
        not make every ``p_i * f_i`` vary in the same direction.

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
        polarities: int | list[int] | None = None,
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
        self._polarities_config = polarities
        self._powerconverter = powerconverter
        self._unit = unit
        self._hardware_unit = hardware_unit

        # Check config
        self.__nbMagnets: int = _get_max_length(curves, calibration_factors, calibration_offsets, crosstalk, polarities)
        self.__calibration_factors = np.ones(self.__nbMagnets)
        self.__calibration_offsets = np.ones(self.__nbMagnets)
        self.__crosstalk = np.ones(self.__nbMagnets)
        self.__polarities = np.ones(self.__nbMagnets)
        self.__curves = _to_list_of_length(curves, self.__nbMagnets)
        self.__sub_models: list[LinearMagnetModel] = []
        self.__current_range = (np.nan, np.nan)

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

        if self._polarities_config is None:
            self.__polarities = np.ones(self.__nbMagnets)
        else:
            self.__polarities = np.array(_to_list_of_length(self._polarities_config, self.__nbMagnets), dtype=float)

        _check_len(self.__calibration_factors, "calibration_factors", self.__nbMagnets)
        _check_len(self.__calibration_offsets, "calibration_offsets", self.__nbMagnets)
        _check_len(self.__crosstalk, "crosstalk", self.__nbMagnets)
        _check_len(self.__polarities, "polarities", self.__nbMagnets)
        _check_len(self.__curves, "curves", self.__nbMagnets)
        if not np.all(np.isin(self.__polarities, (1.0, -1.0))):
            raise PyAMLException(
                f"polarities of the series on {self._powerconverter} must be +1 or -1, got {self.__polarities.tolist()}"
            )

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

        self.__current_range = self.__shared_current_range()
        self.__check_polarities()

    def __shared_current_range(self) -> tuple[float, float]:
        """
        Return the current range shared by all the excitation curves of the series.

        Raises
        ------
        PyAMLException
            If the excitation curves share no current range.
        """
        tables = [curve.get_curve()[:, 0] for curve in self.__curves]
        low = max(float(table.min()) for table in tables)
        high = min(float(table.max()) for table in tables)
        if low >= high:
            raise PyAMLException(
                f"The excitation curves of the series on {self._powerconverter} share no current range ([{low}, {high}])"
            )
        return low, high

    def __check_polarities(self):
        """
        Check that the polarities make every ``p_i * f_i`` vary in the same direction with the hardware value.

        The direction of each curve is taken from the curve itself, with its calibration, so that the check does not
        depend on the magnetic rigidity. A curve with no strength range has no direction and is not checked.

        Raises
        ------
        PyAMLException
            If two magnets vary in opposite directions once multiplied by their polarity.
        """
        low, high = self.__current_range
        directions = []
        for idx, curve in enumerate(self.__curves):
            table = curve.get_curve()
            gain = self.__calibration_factors[idx] * self.__crosstalk[idx]
            span = gain * (np.interp(high, table[:, 0], table[:, 1]) - np.interp(low, table[:, 0], table[:, 1]))
            directions.append(np.sign(self.__polarities[idx] * span))
        directions = np.array(directions)
        if np.any(directions > 0) and np.any(directions < 0):
            raise PyAMLException(
                f"The magnets {np.nonzero(directions < 0)[0].tolist()} of the series on {self._powerconverter} vary in "
                f"the opposite direction to the magnets {np.nonzero(directions > 0)[0].tolist()}: declare polarities "
                f"-1 for the magnets wired in reverse"
            )

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
            Hardware value of the power supply, computed by :meth:`compute_hardware_from_strengths`.
        """
        return np.array([self.compute_hardware_from_strengths(strengths)])

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

        Only the requested magnets define the hardware value, solved as in :meth:`compute_hardware_from_strengths`. The
        other magnets of the series follow the resulting hardware value. A warning is logged when the requested
        strengths cannot all be reached with one hardware value, or when they are outside the excitation curves.

        Parameters
        ----------
        current_hardware : np.array
            Present hardware value of the series, one value per power supply. It is kept when it already gives the
            requested strengths.
        strengths_by_index : dict[int, float]
            Requested strengths, indexed by the position of the magnet in the series.

        Returns
        -------
        np.array
            Hardware value of the power supply, with the shape of ``current_hardware``.

        Raises
        ------
        PyAMLException
            If ``current_hardware`` does not hold one value per power supply of the series, if an excitation curve has
            no strength range, or if an excitation curve is not monotonic.
        """
        _check_len(current_hardware, "current_hardware", len(self.get_device_names()))
        indices = list(strengths_by_index.keys())
        strengths = np.array(list(strengths_by_index.values()), dtype=float)
        return np.array([self._compute_hardware_from_strengths(strengths, indices, float(current_hardware[0]))])

    def compute_mean_strength(self, current: float) -> float:
        """
        Return the average strength of the series for a hardware value.

        Each strength is taken with the declared polarity of its magnet, so that a magnet wired in reverse counts with
        its magnitude instead of cancelling the others.

        Parameters
        ----------
        current : float
            Hardware value shared by the serialized magnets.

        Returns
        -------
        float
            Average strength ``sum(p_i * f_i(I)) / N``, ``p_i`` being the polarity of magnet ``i``.
        """
        return float(np.mean(self._polarities() * self.compute_strengths([current])))

    def compute_hardware_from_mean_strength(self, strength: float, current_hardware: float | None = None) -> float:
        """
        Return the hardware value giving an average strength of the series.

        The average strength is defined as in :meth:`compute_mean_strength`. The polarities make every term vary in the
        same direction, so the average is monotonic. The submodels are piecewise linear in the hardware value, so the
        average is piecewise linear on the union of the curve breakpoints and is inverted exactly by interpolation.
        When every hardware value of an interval gives the requested strength (a plateau), the present hardware value
        clipped to this interval is returned. A strength outside the range reachable by the excitation curves is
        clamped to the end of the shared current range, and a warning is logged.

        Parameters
        ----------
        strength : float
            Requested average strength of the series.
        current_hardware : float, optional
            Present hardware value of the power supply. If omitted, the middle of a plateau is returned.

        Returns
        -------
        float
            Hardware value ``I`` such that ``sum(p_i * f_i(I)) / N == strength``.

        Raises
        ------
        PyAMLException
            If the average strength is not monotonic in the hardware value.
        """
        polarities = self._polarities()
        currents = self._solve_points(range(self.__nbMagnets))
        strengths = np.array([np.mean(polarities * self.compute_strengths([current])) for current in currents])
        steps = np.diff(strengths)
        if np.all(steps >= 0):
            residuals = strengths - strength
        elif np.all(steps <= 0):
            residuals = strength - strengths
        else:
            raise PyAMLException(
                f"Average strength of the series on {self._powerconverter} is not monotonic, it cannot be inverted"
            )
        scale = max(float(np.max(np.abs(strengths))), 1.0)
        if residuals[0] > _SPREAD_RTOL * scale or residuals[-1] < -_SPREAD_RTOL * scale:
            logger.warning(
                f"Strength {strength:.6g} requested for the series on {self._powerconverter} is outside the range "
                f"[{strengths.min():.6g}, {strengths.max():.6g}] reachable by the excitation curves, the hardware value "
                f"is clamped to the end of the curves"
            )
        residuals[np.abs(residuals) < _ZERO_ATOL * scale] = 0.0
        return _pick(_first_zero(currents, residuals), _last_zero(currents, residuals), current_hardware)

    def compute_hardware_from_strengths(self, strengths: np.ndarray, current_hardware: float | None = None) -> float:
        """
        Return the hardware value for a requested strength of each magnet of the series.

        The series has a single hardware value ``I``. It solves ``sum((f_i(I) - k_i) / span_i) == 0``, where ``span_i``
        is the signed strength range ``f_i(I_max) - f_i(I_min)`` of magnet ``i`` on the current range ``[I_min, I_max]``
        shared by all the excitation curves. Each term is dimensionless and increasing, so every magnet weighs the same
        whatever its unit, its polarity or how far its curve is tabulated, and the equation always has a solution,
        exact for a request reachable with one hardware value. When every hardware value of an interval is a solution
        (a plateau), the present hardware value clipped to this interval is returned. When the requested strengths
        cannot all be reached with one hardware value, the result is a compromise and a warning is logged.

        Parameters
        ----------
        strengths : np.ndarray
            Requested strength ``k_i`` of each magnet of the series, in declaration order.
        current_hardware : float, optional
            Present hardware value of the power supply. If omitted, the middle of a plateau is returned.

        Returns
        -------
        float
            Hardware value of the power supply.

        Raises
        ------
        PyAMLException
            If the number of strengths does not match the number of magnets, if an excitation curve has no strength
            range, or if an excitation curve is not monotonic.
        """
        strengths = np.asarray(strengths, dtype=float)
        _check_len(strengths, "strengths", self.__nbMagnets)
        return self._compute_hardware_from_strengths(strengths, list(range(self.__nbMagnets)), current_hardware)

    def _compute_hardware_from_strengths(
        self, strengths: np.ndarray, indices: list[int], current_hardware: float | None = None
    ) -> float:
        """
        Return the hardware value for the requested strengths of some magnets of the series.

        Parameters
        ----------
        strengths : np.ndarray
            Requested strength ``k_i`` of each magnet in ``indices``.
        indices : list[int]
            Positions of the requested magnets in the series.
        current_hardware : float, optional
            Present hardware value of the power supply.

        Returns
        -------
        float
            Hardware value of the power supply.
        """
        current, clamped = self._solve_normalized_residual(strengths, indices, current_hardware)
        if not clamped:
            reached = np.array([self.__sub_models[idx].compute_strengths([current])[0] for idx in indices])
            spans = np.array([self._strength_span(idx) for idx in indices])
            relative_gaps = (reached - strengths) / np.abs(spans)
            if np.any(np.abs(relative_gaps) > _SPREAD_RTOL):
                worst = int(np.argmax(np.abs(relative_gaps)))
                logger.warning(
                    f"Inconsistent strengths requested for the series on {self._powerconverter}: the hardware value "
                    f"{current} misses the requested strengths by up to {reached[worst] - strengths[worst]:.3g} "
                    f"(magnet {indices[worst]}, {100 * relative_gaps[worst]:.3g} % of its curve range)"
                )
        return current

    def _solve_normalized_residual(
        self, strengths: np.ndarray, indices: list[int], current_hardware: float | None = None
    ) -> tuple[float, bool]:
        """
        Solve ``g(I) = sum((f_i(I) - k_i) / span_i) == 0`` over some magnets of the series.

        ``g`` is piecewise linear on the union of the curve breakpoints and increasing, so its zero is found exactly by
        interpolation. When ``g`` is zero on an interval (for example two saturated magnets), the present hardware value
        clipped to the interval is returned, or the middle of the interval when the present hardware value is not
        known. When the zero is outside the shared current range, the hardware value is clamped to the end of this
        range and a warning is logged.

        Parameters
        ----------
        strengths : np.ndarray
            Requested strength ``k_i`` of each magnet in ``indices``.
        indices : list[int]
            Positions of the requested magnets in the series.
        current_hardware : float, optional
            Present hardware value of the power supply.

        Returns
        -------
        tuple[float, bool]
            Hardware value, and whether it was clamped to the end of the shared current range.

        Raises
        ------
        PyAMLException
            If an excitation curve has no strength range, or if an excitation curve is not monotonic.
        """
        spans = np.array([self._strength_span(idx) for idx in indices])
        if np.any(spans == 0.0):
            flat = [idx for idx, span in zip(indices, spans, strict=True) if span == 0.0]
            raise PyAMLException(
                f"Magnets {flat} of the series on {self._powerconverter} have an excitation curve with no strength "
                f"range, the hardware value cannot be computed from their strength"
            )
        currents = self._solve_points(indices)
        residuals = np.array(
            [
                sum(
                    (self.__sub_models[idx].compute_strengths([current])[0] - strength) / span
                    for idx, strength, span in zip(indices, strengths, spans, strict=True)
                )
                for current in currents
            ]
        )
        if np.any(np.diff(residuals) < -_SPREAD_RTOL):
            raise PyAMLException(
                f"An excitation curve of the series on {self._powerconverter} is not monotonic, "
                f"the hardware value cannot be computed"
            )
        residuals[np.abs(residuals) < _ZERO_ATOL] = 0.0
        if residuals[0] > _SPREAD_RTOL or residuals[-1] < -_SPREAD_RTOL:
            current = currents[0] if residuals[0] > 0.0 else currents[-1]
            logger.warning(
                f"Strengths {strengths} requested for the series on {self._powerconverter} are outside the range "
                f"reachable by the excitation curves, the hardware value is clamped to the end of the curves ({current})"
            )
            return float(current), True
        return _pick(_first_zero(currents, residuals), _last_zero(currents, residuals), current_hardware), False

    def _solve_points(self, indices) -> np.ndarray:
        """Return the curve breakpoints of the magnets ``indices`` inside the shared current range, with its ends."""
        low, high = self.__current_range
        breakpoints = np.concatenate([self.__curves[idx].get_curve()[:, 0] for idx in indices])
        inside = breakpoints[(breakpoints > low) & (breakpoints < high)]
        return np.unique(np.concatenate([[low, high], inside]))

    def _strength_span(self, idx: int) -> float:
        """Return the signed strength range ``f_i(I_max) - f_i(I_min)`` of magnet ``idx`` on the shared current range."""
        low, high = self.__current_range
        model = self.__sub_models[idx]
        return float(model.compute_strengths([high])[0] - model.compute_strengths([low])[0])

    def _polarities(self) -> np.ndarray:
        """Return the declared polarity ``p_i`` of each magnet."""
        return self.__polarities

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
