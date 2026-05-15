import numpy as np
from pydantic import BaseModel, ConfigDict

from ..common.element import __pyaml_repr__
from ..common.exception import PyAMLException
from ..configuration.configuration_models import ConfigurationSchema
from ..configuration.curve import Curve, CurveSchema
from ..configuration.inline_curve import InlineCurve, InlineCurveSchema
from ..configuration.matrix import Matrix
from ..configuration.schema_registry import register_schema
from ..control.deviceaccess import DeviceAccess, DeviceAccessSchema
from .linear_model import LinearMagnetModel, LinearMagnetModelSchema
from .model import MagnetModel


class LinearSerializedMagnetModelSchema(ConfigurationSchema):
    """
    Configuration model for linear serialized magnet model

    Parameters
    ----------
    curves : Curve or list[Curve]
        Excitation curves, 1 curve for all or 1 curve per magnet
    calibration_factors : float or list[float], optional
        Correction factor applied to curves, 1 factor for all or 1 factor per magnet.
        Default: ones
    calibration_offsets : float or list[float], optional
        Correction offset applied to curves, 1 offset for all or 1 offset per magnet.
        Default: zeros
    crosstalk : float or list[float], optional
        Crosstalk factors. Default: 1.0
    powerconverter : DeviceAccess
        The hardware can be a single power supply or a list of power supplies.
        If a list is provided, the same value will be affected to all of them
    unit : str
        Strength unit: rad, m-1, m-2
    """

    model_config = ConfigDict(extra="forbid")

    curves: CurveSchema | list[CurveSchema]
    calibration_factors: float | list[float] = None
    calibration_offsets: float | list[float] = None
    crosstalk: float | list[float] = 1.0
    powerconverter: DeviceAccessSchema
    unit: str


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


@register_schema(LinearSerializedMagnetModelSchema)
class LinearSerializedMagnetModel(MagnetModel):
    """
    Class providing a simple linear model for combined function magnets. A matrix
    can handle separation of multipoles. A pseudo current is a linear combination
    of power supply currents associated to a single function.
    """

    def __init__(
        self,
        curves: Curve | list[Curve],
        powerconverter: DeviceAccess,
        unit: str,
        calibration_factors: float | list[float] = None,
        calibration_offsets: float | list[float] = None,
        crosstalk: float | list[float] = 1.0,
    ):
        self._curves = curves
        self._powerconverter = powerconverter
        self._calibration_factors = calibration_factors
        self._calibration_offsets = calibration_offsets
        self._unit = unit
        self.__brho = np.nan

        # Check config
        self.__nbMagnets: int = _get_max_length(
            self._curves, self._calibration_factors, self._calibration_offsets, self._crosstalk
        )
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
            sub_model = LinearMagnetModel(
                curve=self.__curves[magnet_idx],
                calibration_factor=self.__calibration_factors[magnet_idx],
                calibration_offset=self.__calibration_offsets[magnet_idx],
                crosstalk=self.__crosstalk[magnet_idx],
                powerconverter=self._powerconverter,
                unit=self._unit,
            )
            self.__sub_models.append(LinearMagnetModel(sub_model))

    def set_number_of_magnets(self, nb_magnets: int):
        self.__nbMagnets = nb_magnets
        self.__initialize()

    def get_sub_model(self, index: int) -> LinearMagnetModel:
        return self.__sub_models[index]

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        return np.array(
            [model.compute_hardware_values([strength]) for strength, model in zip(strengths, self.__sub_models, strict=True)]
        )

    def compute_strengths(self, currents: np.array) -> np.array:
        return np.array(
            [model.compute_strengths([current]) for current, model in zip(currents, self.__sub_models, strict=True)]
        )

    def get_strength_units(self) -> list[str]:
        return self._units

    def get_hardware_units(self) -> list[str]:
        return [p.unit() for p in self.__sub_models]

    def get_devices(self) -> list[DeviceAccess]:
        return self._powerconverters

    def set_magnet_rigidity(self, brho: np.double):
        self.__brho = brho
        [model.set_magnet_rigidity(brho) for model in self.__sub_models]

    def get_magnet_rigidity(self) -> np.double:
        return self.__brho

    def __repr__(self):
        return __pyaml_repr__(self)
