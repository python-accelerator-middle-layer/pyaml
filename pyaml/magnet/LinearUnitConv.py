import numpy as np
from .UnitConv import UnitConv
from pyaml.configuration.CSVCurve import CSVCurve
from pyaml.configuration.Factory import validate
from pyaml.control.Device import Device

"""
Class that handle manget current/strength conversion using linear interpolation for a single function magnet
"""
class LinearUnitConv(UnitConv):

    @validate
    def __init__(self, curve: CSVCurve, powerconverter: Device, calibration_factor = 1.0,calibration_offset = 0.0, unit: str = None):

        self._curve = curve.get_curve()
        self._curve[:,1] = self._curve[:,1] * calibration_factor + calibration_offset
        self._strength_unit = unit
        self._current_unit = powerconverter.unit
        self._brho = np.nan
        self._ps = powerconverter

    # Compute coil current(s) from magnet strength(s)
    def compute_currents(self,strengths:np.array) -> np.array:
        _current = np.interp(strengths[0] * self._brho,self._curve[:,1],self._curve[:,0])
        return np.array([_current])

    # Compute magnet strength(s) from coil current(s)
    def compute_strengths(self,currents:np.array) -> np.array:
        _strength = np.interp(currents[0],self._curve[:,0],self._curve[:,1]) / self._brho
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
    def send_currents(self,currents:np.array):
        self._ps.set(currents[0])

    # Set magnet rigidity
    def set_magnet_rigidity(self,brho:np.double):
        self._brho = brho

    def __repr__(self):
        return "%s(curve[%d], unit=%s)" % (
            self.__class__.__name__, len(self._curve), self._unit)

def factory_constructor(config: dict) -> LinearUnitConv:
   """Construct a Linear unit conversion object from Yaml config file"""
   return LinearUnitConv(**config)

