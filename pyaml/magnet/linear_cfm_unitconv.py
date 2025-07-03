from pydantic import BaseModel

import numpy as np
from ..configuration.curve import Curve
from ..configuration.matrix import Matrix
from ..control.deviceaccess import DeviceAccess
from .unitconv import UnitConv

# Define the main class name for this module
PYAMLCLASS = "LinearCFMagnetUnitConv"


class ConfigModel(BaseModel):

    multipoles: list[str]
    """List of supported functions: A0,B0,A1,B1,etc (i.e) [B0,A1,B2]"""
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
    powerconverters: list[DeviceAccess]
    """List of power converter devices to apply currrents (can be different
       from number of function)"""
    matrix: Matrix = None
    """n x m matrix (n rows for n function , m columns for m currents) 
       to handle multipoles separation. Default: Identity"""
    units: list[str]
    """List of strength unit (i.e. ['rad','m-1','m-2'])"""


class LinearCFMagnetUnitConv(UnitConv):
    """
    Class providing a simple linear model for combined function magnets. A matrix
    can handle separation of multipoles. A pseudo current is a linear combination
    of power supply currents assiociated to a single function.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

        # Check config
        self._nbFunction: int = len(cfg.multipoles)
        self._nbPS: int = len(cfg.powerconverters)

        if cfg.calibration_factors is None:
            self._calibration_factors = np.ones(self._nbFunction)
        else:
            self._calibration_factors = cfg.calibration_factors

        if cfg.calibration_offsets is None:
            self._calibration_offsets = np.zeros(self._nbFunction)
        else:
            self._calibration_offsets = cfg.calibration_offsets

        if cfg.pseudo_factors is None:
            self._pf = np.ones(self._nbFunction)
        else:
            self._pf = cfg.pseudo_factors

        if len(self._calibration_factors) != self._nbFunction:
            raise Exception(
                "calibration_factors does not have the expected "
                "number of items ({self._nbFunction} expected)"
            )
        if len(self._calibration_offsets) != self._nbFunction:
            raise Exception(
                "calibration_offsets does not have the expected "
                "number of items ({self._nbFunction} expected)"
            )
        if len(self._pf) != self._nbFunction:
            raise Exception(
                "pseudo_factors does not have the expected "
                "number of items ({self._nbFunction} expected)"
            )
        if len(cfg.units) != self._nbFunction:
            raise Exception(
                "units does not have the expected "
                "number of items ({self._nbFunction} expected)"
            )
        if len(cfg.curves) != self._nbFunction:
            raise Exception(
                "curves does not have the expected "
                "number of items ({self._nbFunction} expected)"
            )

        if cfg.matrix is None:
            self._matrix = np.identity(self._nbFunction)
        else:
            self._matrix = cfg.matrix.get_matrix()

        _s = np.shape(self._matrix)

        if len(_s) != 2 or _s[0] != self._nbFunction or _s[1] != self._nbPS:
            raise Exception(
                "matrix wrong dimension "
                "({self._nbFunction}x{self._nbPS} expected but got {_s[0]}x{_s[1]})"
            )

        # Apply factor and offset
        for idx, c in enumerate(cfg.curves):
            c.get_curve()[:, 1] *= self._calibration_factors[idx]
            c.get_curve()[:, 1] += self._calibration_offsets[idx]

        # Compute pseudo inverse
        self._inv = np.linalg.pinv(self._matrix)

    # Get coil current(s) from magnet strength(s)
    def compute_currents(self, strengths: np.array) -> np.array:
        _pI = np.zeros(self._nbFunction)
        for idx, c in enumerate(self._cfg.curves):
            _pI[idx] = self._pf[idx] * np.interp(
                strengths[idx] * self._brho, c.get_curve()[:, 1], c.get_curve()[:, 0]
            )
        _currents = np.matmul(self._inv, _pI)
        return _currents

    # Get magnet strength(s) from coil current(s)
    def compute_strengths(self, currents: np.array) -> np.array:
        _strength = np.zeros(self._nbFunction)
        _pI = np.matmul(self._matrix, currents)
        for idx, c in enumerate(self._cfg.curves):
            _strength[idx] = (
                np.interp(
                    self._pf[idx] * _pI[idx], c.get_curve()[:, 0], c.get_curve()[:, 1]
                )
                / self._brho
            )
        return _strength

    # Get strength units
    def get_strength_units(self) -> list[str]:
        return self._cfg.units

    # Get current units
    def get_current_units(self) -> list[str]:
        _u = []
        for p in self._cfg.powerconverters:
            _u.append(p.unit())
        return np.array(_u)

    # Get power supply current setpoint(s) from control system
    def read_currents(self) -> np.array:
        _c = []
        for p in self._cfg.powerconverters:
            _c.append(p.get())
        return np.array(_c)

    # Get power supply current(s) from control system
    def readback_currents(self) -> np.array:
        _c = []
        for p in self._cfg.powerconverters:
            _c.append(p.readback())
        return np.array(_c)

    # Send power supply current(s) to control system
    def send_currents(self, currents: np.array):
        for idx, p in enumerate(self._cfg.powerconverters):
            p.set(currents[idx])

    # Set magnet rigidity
    def set_magnet_rigidity(self, brho: np.double):
        self._brho = brho
