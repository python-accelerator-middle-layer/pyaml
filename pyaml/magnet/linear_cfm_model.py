from ..configuration.curve import Curve
from ..configuration.matrix import Matrix
from ..control.deviceaccess import DeviceAccess
from .model import MagnetModel
from ..common.exception import PyAMLException
from ..common.element import __pyaml_repr__

from pydantic import BaseModel,ConfigDict
import numpy as np

# Define the main class name for this module
PYAMLCLASS = "LinearCFMagnetModel"


class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    multipoles: list[str]
    """List of supported functions: A0,B0,A1,B1,etc (i.e. [B0,A1,B2])"""
    curves: list[Curve]
    """Exitacion curves, 1 curve per function"""
    calibration_factors: list[float] = None
    """Correction factor applied to curves, 1 factor per function
       Delfault: ones"""
    calibration_offsets: list[float] = None
    """Correction offset applied to curves, 1 offset per function
       Delfault: zeros"""
    pseudo_factors: list[float] = None
    """Factors applied to 'pseudo currents', 1 factor per function.
       Delfault: ones"""
    pseudo_offsets: list[float] = None
    """Offsets applied to 'pseudo currents', 1 factor per function.
       Delfault: zeros"""
    powerconverters: list[DeviceAccess]
    """List of power converter devices to apply currrents (can be different
       from number of function)"""
    matrix: Matrix = None
    """n x m matrix (n rows for n function , m columns for m currents) 
       to handle multipoles separation. Default: Identity"""
    units: list[str]
    """List of strength unit (i.e. ['rad','m-1','m-2'])"""


class LinearCFMagnetModel(MagnetModel):
    """
    Class providing a simple linear model for combined function magnets. A matrix
    can handle separation of multipoles. A pseudo current is a linear combination
    of power supply currents assiociated to a single function.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

        # Check config
        self.__nbFunction: int = len(cfg.multipoles)
        self.__nbPS: int = len(cfg.powerconverters)

        if cfg.calibration_factors is None:
            self.__calibration_factors = np.ones(self.__nbFunction)
        else:
            self.__calibration_factors = cfg.calibration_factors

        if cfg.calibration_offsets is None:
            self.__calibration_offsets = np.zeros(self.__nbFunction)
        else:
            self.__calibration_offsets = cfg.calibration_offsets

        if cfg.pseudo_factors is None:
            self.__pf = np.ones(self.__nbFunction)
        else:
            self.__pf = cfg.pseudo_factors

        if cfg.pseudo_offsets is None:
            self.__po = np.zeros(self.__nbFunction)
        else:
            self.__po = cfg.pseudo_factors

        self.__check_len(self.__calibration_factors,"calibration_factors",self.__nbFunction)
        self.__check_len(self.__calibration_offsets,"calibration_offsets",self.__nbFunction)
        self.__check_len(self.__pf,"pseudo_factors",self.__nbFunction)
        self.__check_len(self.__po,"pseudo_offsets",self.__nbFunction)
        self.__check_len(cfg.units,"units",self.__nbFunction)
        self.__check_len(cfg.curves,"curves",self.__nbFunction)

        if cfg.matrix is None:
            self.__matrix = np.identity(self.__nbFunction)
        else:
            self.__matrix = cfg.matrix.get_matrix()

        _s = np.shape(self.__matrix)

        if len(_s) != 2 or _s[0] != self.__nbFunction or _s[1] != self.__nbPS:
            raise PyAMLException(
                "matrix wrong dimension "
                f"({self.__nbFunction}x{self.__nbPS} expected but got {_s[0]}x{_s[1]})"
            )
        
        self.__curves = []
        self.__rcurves = []

        # Apply factor and offset
        for idx, c in enumerate(cfg.curves):
            self.__curves.append(c.get_curve())
            self.__curves[idx][:, 1] *= self.__calibration_factors[idx]
            self.__curves[idx][:, 1] += self.__calibration_offsets[idx]
            self.__rcurves.append(Curve.inverse(self.__curves[idx]))

        # Compute pseudo inverse
        self.__inv = np.linalg.pinv(self.__matrix)


    def __check_len(self,obj,name,expected_len):
        lgth = len(obj) 
        if lgth != expected_len:
            raise PyAMLException(
                f"{name} does not have the expected "
                f"number of items ({expected_len} items expected but got {lgth})"
            )    

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        _pI = np.zeros(self.__nbFunction)
        for idx, c in enumerate(self.__rcurves):
            _pI[idx] = self.__pf[idx] * np.interp(
                strengths[idx] * self._brho, c[:, 0], c[:, 1]
            ) + self.__po[idx]
        _currents = np.matmul(self.__inv, _pI)
        return _currents

    def compute_strengths(self, currents: np.array) -> np.array:
        _strength = np.zeros(self.__nbFunction)
        _pI = np.matmul(self.__matrix, currents)
        for idx, c in enumerate(self.__curves):
            _strength[idx] = (
                np.interp(
                    (_pI[idx] - self.__po[idx]) / self.__pf[idx],  c[:, 0], c[:, 1]
                )
                / self._brho
            )
        return _strength

    def get_strength_units(self) -> list[str]:
        return self._cfg.units

    def get_hardware_units(self) -> list[str]:
        return np.array([p.unit() for p in self._cfg.powerconverters])

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
        return (self.__nbPS == self.__nbFunction) and np.allclose(self.__matrix, np.eye(self.__nbFunction))

    def __repr__(self):
        return __pyaml_repr__(self)

