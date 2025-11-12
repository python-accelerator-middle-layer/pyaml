from pathlib import Path

import numpy as np
from pydantic import BaseModel,ConfigDict
from scipy.constants import speed_of_light

from pyaml.configuration.curve import Curve
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.readback_value import Value
from pyaml.configuration import get_root_folder

PYAMLCLASS : str = "AttributeWithTangoMockingBehaviour"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    attribute: str
    calibration_factor: float = 1.0
    """Correction factor applied to the curve"""
    calibration_offset: float = 0.0
    """Correction offset applied to the curve")"""
    crosstalk: float = 1.0
    """Crosstalk factor"""
    magnet_energy: float = 0.0
    curve: str = None
    unit: str = ""

class TangoDevice:
    def __init__(self, name: str):
        self.name = name
        self._current:float = 0.0
        self._strength:float = 0.0
        self._attributes:dict[str, float] = {}
        self.__calibration_factor: float = 1.0
        self.__calibration_offset: float = 0.0
        self.__brho: float = np.nan
        self._curve_file: str = ""
        self.__curve = None
        self.__rcurve = None

    def read(self, attr_name: str) -> float:
        if attr_name == "current":
            return self._current
        elif attr_name == "strength":
            return self._strength
        else:
            if attr_name in self._attributes:
                return self._attributes[attr_name]
            else:
                return 0.0

    def write(self, attr_name: str, value: float):
        if attr_name == "current":
            self._current = value
            self.__compute_strength()
        elif attr_name == "strength":
            self._strength = value
            self.__compute_current()
        else:
            self._attributes[attr_name] = value

    def __compute_strength(self):
        if self.__curve is not None:
            self._strength = self.compute_strengths(np.array([self._current]))[0]

    def __compute_current(self):
        if self.__curve is not None:
            self._current = self.compute_hardware_values(np.array([self._strength]))[0]

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        _current = np.interp(
            strengths[0] * self.__brho, self.__rcurve[:, 0], self.__rcurve[:, 1]
        )
        return np.array([_current])

    def compute_strengths(self, currents: np.array) -> np.array:
        _strength = (
            np.interp(currents[0], self.__curve[:, 0], self.__curve[:, 1]) / self.__brho
        )
        return np.array([_strength])

    def set_magnet_model_data(self: float, calibration_factor, calibration_offset: float, crosstalk: float, magnet_energy: float, curve_file: str):
        self.__calibration_factor = calibration_factor
        self.__calibration_offset = calibration_offset
        self.__brho = magnet_energy / speed_of_light
        self._curve_file = curve_file
        path:Path = get_root_folder() / curve_file
        self.__curve = np.genfromtxt(path, delimiter=",", dtype=float)
        _s = np.shape(self.__curve)
        if len(_s) != 2 or _s[1] != 2:
            raise Exception(curve_file + " wrong dimension")
        self.__curve[:, 1] = (
            self.__curve[:, 1] * calibration_factor * crosstalk + calibration_offset
        )
        self.__rcurve = Curve.inverse(self.__curve)


TANGO_DEVICES:dict[str, TangoDevice] = {}

def get_device(name: str) -> TangoDevice:
    if name in TANGO_DEVICES:
        device = TANGO_DEVICES[name]
    else:
        device = TangoDevice(name)
        TANGO_DEVICES[name] = device
    return device

class AttributeWithTangoMockingBehaviour(DeviceAccess):
    """
    Class that implements a default device class that just prints out 
    values (Debugging purpose)
    """
    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg
        self._setpoint = cfg.attribute
        self._readback = cfg.attribute
        self._unit = cfg.unit
        self._device_name, self._attribute_name = cfg.attribute.rsplit("/", 1)
        self._device = get_device(self._device_name)
        if cfg.curve is not None:
            self._device.set_magnet_model_data(cfg.calibration_factor, cfg.calibration_offset, cfg.crosstalk, cfg.magnet_energy, cfg.curve)

    def name(self) -> str:
        return self._setpoint

    def measure_name(self) -> str:
        return self._readback

    def set(self, value: float):
        self._device.write(self._attribute_name, value)

    def set_and_wait(self, value: float):
        self._device.write(self._attribute_name, value)

    def get(self) -> float:
        return self._device.read(self._attribute_name)

    def readback(self) -> Value:
        return Value(self.get())

    def unit(self) -> str:
        return self._unit
