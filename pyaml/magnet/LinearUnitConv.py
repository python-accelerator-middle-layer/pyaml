from pathlib import Path

import numpy as np
from pydantic import field_validator

from . import UnitConv
from ..configuration.models import recursively_construct_element_from_cfg
from ..configuration import CSVCurve
from ..control import Device

"""
Class that handle manget current/strength conversion using linear interpolation for a single function magnet
"""


class Config(UnitConv.Config):
    curve: str | Path | CSVCurve.Config
    powerconverter: str | Path | Device.Config
    calibration_factor: float = 1.0
    calibration_offset: float = 0.0

    @field_validator("curve", mode="before")
    def validate_curve(cls, v, values):
        return cls.validate_sub_config(v, values, "curve", CSVCurve.Config)


class LinearUnitConv(UnitConv.UnitConv):

    def __init__(self, cfg: Config):

        self._cfg = cfg
        curve_obj = recursively_construct_element_from_cfg(cfg.curve)
        self._curve = curve_obj.get_curve()
        self._curve[:, 1] = (
            self._curve[:, 1] * cfg.calibration_factor + cfg.calibration_offset
        )
        self._strength_unit = cfg.unit
        self._current_unit = cfg.powerconverter.unit
        self._brho = np.nan
        self._ps = Device.Device(cfg.powerconverter)

    # Compute coil current(s) from magnet strength(s)
    def compute_currents(self, strengths: np.array) -> np.array:
        _current = np.interp(
            strengths[0] * self._brho, self._curve[:, 1], self._curve[:, 0]
        )
        return np.array([_current])

    # Compute magnet strength(s) from coil current(s)
    def compute_strengths(self, currents: np.array) -> np.array:
        _strength = (
            np.interp(currents[0], self._curve[:, 0], self._curve[:, 1]) / self._brho
        )
        return np.array([_strength])

    # Get strength units
    def get_strengths_units(self) -> list[str]:
        return [self._strength_unit] if self._strength_unit is not None else [""]

    # Get current units
    def get_current_units(self) -> list[str]:
        return [self._current_unit] if self._current_unit is not None else [""]

    # Get power supply current setpoint(s) from control system
    def read_currents(self) -> np.array:
        return [self._ps.get()]

    # Get power supply current(s) from control system
    def readback_currents(self) -> np.array:
        pass

    # Send power supply current(s) to control system
    def send_currents(self, currents: np.array):
        self._ps.set(currents[0])

    # Set magnet rigidity
    def set_magnet_rigidity(self, brho: np.double):
        self._brho = brho

    def __repr__(self):
        return "%s(curve[%d], unit=%s)" % (
            self.__class__.__name__,
            len(self._curve),
            self._unit,
        )
