from ..configuration.curve import Curve
from ..configuration.matrix import Matrix
from ..control.deviceaccess import DeviceAccess
from .model import MagnetModel
from .linear_model import ConfigModel as LinearConfigModel, LinearMagnetModel
from ..common.exception import PyAMLException
from ..common.element import __pyaml_repr__

from pydantic import BaseModel, ConfigDict
import numpy as np

# Define the main class name for this module
PYAMLCLASS = "LinearSerializedMagnetModel"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    curves: Curve|list[Curve]
    """Excitation curves, 1 curve for all or 1 curve per magnet"""
    calibration_factors: float|list[float] = None
    """Correction factor applied to curves, 1 factor for all or 1 factor per magnet
       Delfault: ones"""
    calibration_offsets: float|list[float] = None
    """Correction offset applied to curves, 1 offset for all or 1 offset per magnet
       Delfault: zeros"""
    crosstalk: float|list[float] = 1.0
    """Crosstalk factors"""
    powerconverters: DeviceAccess | list[DeviceAccess]
    """
    The hardware can be a single power supply or a list of power supplies.
    If a list is provided, the same value will be affected to all of them.
    """
    matrix: Matrix = None
    """n x m matrix (n rows for n magnets , m columns for m currents) 
       to handle magnets separations. Default: Identity"""
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

def _to_list_of_length(elem, length:int) ->list:
    if isinstance(elem, list):
        return elem
    else:
        return [elem]*length


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

        # Check config
        self.__nbMagnets: int = _get_max_length(cfg.curves, cfg.calibration_factors, cfg.calibration_offsets,
                                               cfg.powerconverters, cfg.crosstalk)
        self.__nbPS: int = _get_length(cfg.powerconverters)

        if cfg.calibration_factors is None:
            self.__calibration_factors = np.ones(self.__nbMagnets)
        else:
            self.__calibration_factors = _to_list_of_length(cfg.calibration_factors, self.__nbMagnets)

        if cfg.calibration_offsets is None:
            self.__calibration_offsets = np.zeros(self.__nbMagnets)
        else:
            self.__calibration_offsets = _to_list_of_length(cfg.calibration_offsets, self.__nbMagnets)

        if cfg.crosstalk is None:
            self.__crosstalk = np.zeros(self.__nbMagnets)
        else:
            self.__crosstalk = _to_list_of_length(cfg.crosstalk, self.__nbMagnets)
        self.__curves = _to_list_of_length(cfg.curves, self.__nbMagnets)
        powerconverters = _to_list_of_length(cfg.powerconverters, self.__nbPS)

        _check_len(self.__calibration_factors, "calibration_factors", self.__nbMagnets)
        _check_len(self.__calibration_offsets, "calibration_offsets", self.__nbMagnets)
        _check_len(self.__crosstalk, "crosstalk", self.__nbMagnets)
        _check_len(self.__curves, "curves", self.__nbMagnets)
        _check_len(powerconverters, "powerconverters", self.__nbPS)

        if 1 < self.__nbPS < self.__nbMagnets and cfg.matrix is None:
            raise PyAMLException(
                "Wrong number of powersupply<->magnets or a matrix must be provided."
            )

        if cfg.matrix is None:
            mat:list[list[int]] = []
            for magnet_idx in range(self.__nbMagnets):
                magnet_affectation = []
                for powerconverter_idx in range(self.__nbPS):
                    if powerconverter_idx==magnet_idx or self.__nbPS==1:
                        magnet_affectation.append(1)
                    else:
                        magnet_affectation.append(0)
                mat.append(magnet_affectation)
            self.__matrix = np.matrix(mat)
        else:
            self.__matrix = cfg.matrix.get_matrix()

        _s = np.shape(self.__matrix)
        sum_matrix = np.sum(self.__matrix)

        if len(_s) != 2 or _s[0] != self.__nbMagnets or _s[1] != self.__nbPS:
            raise PyAMLException(
                "matrix wrong dimension "
                f"({self.__nbMagnets}x{self.__nbPS} expected but got {_s[0]}x{_s[1]})"
            )

        if sum_matrix != self.__nbMagnets:
            raise PyAMLException("Wrong matrix, the sum must equal the number of magnets")

        self.__sub_models:list[LinearMagnetModel] = []
        for magnet_idx in range(_s[0]):
            for powerconverter_idx in range(_s[1]):
                if self.__matrix[magnet_idx, powerconverter_idx] != 0:
                    sub_model = LinearConfigModel(curve=self.__curves[magnet_idx],
                                                  calibration_factor=self.__calibration_factors[magnet_idx],
                                                  calibration_offset= self.__calibration_offsets[magnet_idx],
                                                  crosstalk=self.__crosstalk[magnet_idx],
                                                  powerconverter=powerconverters[powerconverter_idx],
                                                  unit=self._cfg.unit)
                    self.__sub_models.append(LinearMagnetModel(sub_model))

    def get_sub_model(self, index:int) -> LinearMagnetModel:
        if len(self.__sub_models) == 1:
            return self.__sub_models[0]
        else:
            return self.__sub_models[index]

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        return np.array([model.compute_hardware_values([strength]) for strength, model in zip(strengths, self.__sub_models)])

    def compute_strengths(self, currents: np.array) -> np.array:
        return np.array([model.compute_strengths([current]) for current, model in zip(currents, self.__sub_models)])

    def get_strength_units(self) -> list[str]:
        return self._cfg.units

    def get_hardware_units(self) -> list[str]:
        return [p.unit() for p in self._cfg.__sub_models]

    def read_hardware_values(self) -> np.array:
        return np.array([p.get() for p in self._cfg.__sub_models])

    def readback_hardware_values(self) -> np.array:
        return np.array([p.readback() for p in self._cfg.__sub_models])

    def send_hardware_values(self, currents: np.array):
        for idx, p in enumerate(self._cfg.__sub_models):
            p.set(currents[idx])

    def get_devices(self) -> list[DeviceAccess]:
        return self._cfg.powerconverters

    def set_magnet_rigidity(self, brho: np.double):
        [model.set_magnet_rigidity(brho) for model in self.__sub_models]

    def has_hardware(self) -> bool:
        return self.__nbPS >0

    def __repr__(self):
        return __pyaml_repr__(self)

