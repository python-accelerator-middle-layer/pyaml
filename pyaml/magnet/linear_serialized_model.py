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


def _get_length(elem) -> int:
    if elem is None:
        return 0
    if isinstance(elem, list):
        return len(elem)
    else:
        return 1


def _get_max_length(*args, **kwargs) -> int:
    max_args = max([_get_length(elem) for elem in args]) if args else 0
    max_kwargs = max([_get_length(elem) for elem in kwargs.values()]) if kwargs else 0
    return max(max_args, max_kwargs)


def _to_list_of_length(elem, length: int) -> list:
    if isinstance(elem, list):
        return elem
    else:
        return [elem] * length


def _check_len(obj, name, expected_length):
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

    Notes
    -----
    The number of magnets is inferred from the longest list among the supplied
    configuration values. Scalars are expanded to match that length.
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
        self.__nbMagnets = nb_magnets
        self.__initialize()

    def get_sub_model(self, index: int) -> LinearMagnetModel:
        return self.__sub_models[index]

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        currents = [model.compute_hardware_values([s])[0] for s, model in zip(strengths, self.__sub_models, strict=True)]
        return np.array([np.mean(currents)])

    def compute_strengths(self, currents: np.array) -> np.array:
        current = currents[0]
        return np.array([model.compute_strengths([current])[0] for model in self.__sub_models])

    def get_strength_units(self) -> list[str]:
        return [self._unit] * self.__nbMagnets

    def get_hardware_units(self) -> list[str]:
        return [self._hardware_unit]

    def get_device_names(self) -> list[str | None]:
        return [self._powerconverter]

    def set_magnet_rigidity(self, brho: np.double):
        self.__brho = brho
        [model.set_magnet_rigidity(brho) for model in self.__sub_models]

    def get_magnet_rigidity(self) -> np.double:
        return self.__brho

    def __repr__(self):
        return __pyaml_repr__(self)
