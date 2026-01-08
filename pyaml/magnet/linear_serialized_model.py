import numpy as np
from pydantic import BaseModel, ConfigDict

from ..common.element import __pyaml_repr__
from ..common.exception import PyAMLException
from ..configuration.curve import Curve
from ..configuration.inline_curve import ConfigModel as InlineCurveModel
from ..configuration.inline_curve import InlineCurve
from ..configuration.matrix import Matrix
from ..control.deviceaccess import DeviceAccess
from .linear_model import ConfigModel as LinearConfigModel
from .linear_model import LinearMagnetModel
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "LinearSerializedMagnetModel"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    curves: Curve | list[Curve]
    """Excitation curves, 1 curve for all or 1 curve per magnet"""
    calibration_factors: float | list[float] = None
    """Correction factor applied to curves, 1 factor for all or 1 factor per magnet
       Delfault: ones"""
    calibration_offsets: float | list[float] = None
    """Correction offset applied to curves, 1 offset for all or 1 offset per magnet
       Delfault: zeros"""
    crosstalk: float | list[float] = 1.0
    """Crosstalk factors"""
    powerconverter: DeviceAccess
    """
    The hardware can be a single power supply or a list of power supplies.
    If a list is provided, the same value will be affected to all of them.
    """
    unit: str
    """Strength unit: rad, m-1, m-2"""


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
            f"{name} does not have the expected "
            f"number of items ({expected_length} items expected but got {length})"
        )


class LinearSerializedMagnetModel(MagnetModel):
    """
    Class providing a simple linear model for combined function magnets. A matrix
    can handle separation of multipoles. A pseudo current is a linear combination
    of power supply currents associated to a single function.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self.__brho = np.nan

        # Check config
        self.__nbMagnets: int = _get_max_length(
            cfg.curves, cfg.calibration_factors, cfg.calibration_offsets, cfg.crosstalk
        )
        self.__calibration_factors = np.ones(self.__nbMagnets)
        self.__calibration_offsets = np.ones(self.__nbMagnets)
        self.__crosstalk = np.ones(self.__nbMagnets)
        self.__curves = _to_list_of_length(self._cfg.curves, self.__nbMagnets)
        self.__sub_models: list[LinearMagnetModel] = []

    def __initialize(self):
        if self._cfg.calibration_factors is None:
            self.__calibration_factors = np.ones(self.__nbMagnets)
        else:
            self.__calibration_factors = _to_list_of_length(
                self._cfg.calibration_factors, self.__nbMagnets
            )

        if self._cfg.calibration_offsets is None:
            self.__calibration_offsets = np.zeros(self.__nbMagnets)
        else:
            self.__calibration_offsets = _to_list_of_length(
                self._cfg.calibration_offsets, self.__nbMagnets
            )

        if self._cfg.crosstalk is None:
            self.__crosstalk = np.zeros(self.__nbMagnets)
        else:
            self.__crosstalk = _to_list_of_length(self._cfg.crosstalk, self.__nbMagnets)
        self.__curves = _to_list_of_length(self._cfg.curves, self.__nbMagnets)
        if isinstance(self._cfg.curves, list):
            self.__curves = self._cfg.curves
        else:
            self.__curves: list[Curve] = []
            for _ in range(self.__nbMagnets):
                curve = InlineCurve(InlineCurveModel(mat=self._cfg.curves.get_curve()))
                self.__curves.append(curve)

        _check_len(self.__calibration_factors, "calibration_factors", self.__nbMagnets)
        _check_len(self.__calibration_offsets, "calibration_offsets", self.__nbMagnets)
        _check_len(self.__crosstalk, "crosstalk", self.__nbMagnets)
        _check_len(self.__curves, "curves", self.__nbMagnets)

        self.__sub_models: list[LinearMagnetModel] = []
        for magnet_idx in range(self.__nbMagnets):
            sub_model = LinearConfigModel(
                curve=self.__curves[magnet_idx],
                calibration_factor=self.__calibration_factors[magnet_idx],
                calibration_offset=self.__calibration_offsets[magnet_idx],
                crosstalk=self.__crosstalk[magnet_idx],
                powerconverter=self._cfg.powerconverter,
                unit=self._cfg.unit,
            )
            self.__sub_models.append(LinearMagnetModel(sub_model))

    def set_number_of_magnets(self, nb_magnets: int):
        self.__nbMagnets = nb_magnets
        self.__initialize()

    def get_sub_model(self, index: int) -> LinearMagnetModel:
        return self.__sub_models[index]

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        return np.array(
            [
                model.compute_hardware_values([strength])
                for strength, model in zip(strengths, self.__sub_models)
            ]
        )

    def compute_strengths(self, currents: np.array) -> np.array:
        return np.array(
            [
                model.compute_strengths([current])
                for current, model in zip(currents, self.__sub_models)
            ]
        )

    def get_strength_units(self) -> list[str]:
        return self._cfg.units

    def get_hardware_units(self) -> list[str]:
        return [p.unit() for p in self._cfg.__sub_models]

    def get_devices(self) -> list[DeviceAccess]:
        return self._cfg.powerconverters

    def set_magnet_rigidity(self, brho: np.double):
        self.__brho = brho
        [model.set_magnet_rigidity(brho) for model in self.__sub_models]

    def get_magnet_rigidity(self) -> np.double:
        return self.__brho

    def __repr__(self):
        return __pyaml_repr__(self)
