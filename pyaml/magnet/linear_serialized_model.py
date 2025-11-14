from ..configuration.curve import Curve
from ..configuration.matrix import Matrix
from ..control.deviceaccess import DeviceAccess
from .model import MagnetModel
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
    pseudo_factors: float|list[float] = None
    """Factors applied to 'pseudo currents', 1 factor for all or 1 factor per magnet.
       Delfault: ones"""
    pseudo_offsets: float|list[float] = None
    """Offsets applied to 'pseudo currents', 1 factor for all or 1 factor per magnet.
       Delfault: zeros"""
    matrix: Matrix = None
    """n x m matrix (n rows for n magnets , m columns for m currents) 
       to handle magnets separations. Default: Identity"""
    powerconverters: DeviceAccess | list[DeviceAccess]
    """
    The hardware can be a single power supply or a list of power supplies.
    If a list is provided, the same value will be affected to all of them.
    """
    unit: str
    """Strength unit: rad, m-1, m-2"""


def get_length(elem) -> int:
    if isinstance(elem, list):
        return len(elem)
    else:
        return 1

def get_max_length(*args, **kwargs) -> int:
    max_args = max([get_length(elem) for elem in args]) if args else 0
    max_kwargs = max([get_length(elem) for elem in kwargs.values()]) if kwargs else 0
    return max(max_args, max_kwargs)

def to_list_of_length(elem, length:int) ->list:
    if isinstance(elem, list):
        return elem
    else:
        return [elem]*length

class LinearSerializedMagnetModel(MagnetModel):
    """
    Class providing a simple linear model for combined function magnets. A matrix
    can handle separation of multipoles. A pseudo current is a linear combination
    of power supply currents associated to a single function.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self._brho = np.nan

        # Check config
        self.__nbMagnets: int = get_max_length(cfg.curves, cfg.calibration_factors, cfg.calibration_offsets,
                                               cfg.pseudo_factors, cfg.pseudo_offsets, cfg.powerconverters)
        self.__nbPS: int = get_length(cfg.powerconverters)

        if cfg.calibration_factors is None:
            self.__calibration_factors = np.ones(self.__nbMagnets)
        else:
            self.__calibration_factors = to_list_of_length(cfg.calibration_factors, self.__nbMagnets)

        if cfg.calibration_offsets is None:
            self.__calibration_offsets = np.zeros(self.__nbMagnets)
        else:
            self.__calibration_offsets = to_list_of_length(cfg.calibration_offsets, self.__nbMagnets)

        if cfg.pseudo_factors is None:
            self.__pf = np.ones(self.__nbMagnets)
        else:
            self.__pf = to_list_of_length(cfg.pseudo_factors, self.__nbMagnets)

        if cfg.pseudo_offsets is None:
            self.__po = np.zeros(self.__nbMagnets)
        else:
            self.__po = to_list_of_length(cfg.pseudo_factors, self.__nbMagnets)

        self.__check_len(self.__calibration_factors, "calibration_factors", self.__nbMagnets)
        self.__check_len(self.__calibration_offsets, "calibration_offsets", self.__nbMagnets)
        self.__check_len(self.__pf, "pseudo_factors", self.__nbMagnets)
        self.__check_len(self.__po, "pseudo_offsets", self.__nbMagnets)
        if isinstance(cfg.curves, list):
            self.__check_len(cfg.curves, "curves", self.__nbMagnets)

        if cfg.matrix is None:
            self.__matrix = np.identity(self.__nbMagnets)
        else:
            self.__matrix = cfg.matrix.get_matrix()

        _s = np.shape(self.__matrix)

        if len(_s) != 2 or _s[0] != self.__nbMagnets or _s[1] != self.__nbPS:
            raise PyAMLException(
                "matrix wrong dimension "
                f"({self.__nbMagnets}x{self.__nbPS} expected but got {_s[0]}x{_s[1]})"
            )

        self.__curves = []
        self.__rcurves = []

        # Apply factor and offset
        if isinstance(cfg.curves, list):
            curves = cfg.curves
        else:
            curves = [cfg.curves]
        for idx, c in enumerate(curves):
            self.__curves.append(c.get_curve())
            self.__curves[idx][:, 1] *= self.__calibration_factors[idx]
            self.__curves[idx][:, 1] += self.__calibration_offsets[idx]
            self.__rcurves.append(Curve.inverse(self.__curves[idx]))

        # Compute pseudo inverse
        self.__inv = np.linalg.pinv(self.__matrix)

    def __check_len(self, obj, name, expected_len):
        lgth = len(obj)
        if lgth != expected_len:
            raise PyAMLException(
                f"{name} does not have the expected "
                f"number of items ({expected_len} items expected but got {lgth})"
            )

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        _pI = np.zeros(self.__nbMagnets)
        for idx, c in enumerate(self.__rcurves):
            _pI[idx] = self.__pf[idx] * np.interp(
                strengths[idx] * self._brho, c[:, 0], c[:, 1]
            ) + self.__po[idx]
        _currents = np.matmul(self.__inv, _pI)
        return _currents

    def compute_strengths(self, currents: np.array) -> np.array:
        _strength = np.zeros(self.__nbMagnets)
        _pI = np.matmul(self.__matrix, currents)
        for idx, c in enumerate(self.__curves):
            _strength[idx] = (
                    np.interp(
                        (_pI[idx] - self.__po[idx]) / self.__pf[idx], c[:, 0], c[:, 1]
                    )
                    / self._brho
            )
        return _strength

    def get_strength_units(self) -> list[str]:
        return self._cfg.units

    def get_hardware_units(self) -> list[str]:
        return [p.unit() for p in self._cfg.powerconverters]

    def read_hardware_values(self) -> np.array:
        return np.array([p.get() for p in self._cfg.powerconverters])

    def readback_hardware_values(self) -> np.array:
        return np.array([p.readback() for p in self._cfg.powerconverters])

    def send_hardware_values(self, currents: np.array):
        for idx, p in enumerate(self._cfg.powerconverters):
            p.set(currents[idx])

    def get_devices(self) -> list[DeviceAccess]:
        return self._cfg.powerconverters

    def set_magnet_rigidity(self, brho: np.double):
        self._brho = brho

    def has_hardware(self) -> bool:
        return (self.__nbPS == self.__nbMagnets) and np.allclose(self.__matrix, np.eye(self.__nbMagnets))

    def __repr__(self):
        return __pyaml_repr__(self)

