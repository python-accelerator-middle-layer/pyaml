import numpy as np
from .UnitConv import UnitConv

class LinearUnitConv(UnitConv):

    def __init__(self, calibration_factor = 1.0,calibration_offset = 0.0, curve: list = None, powerconverter: dict = None, unit: str = None):
        print("LinearUnitConv()")
        self.calibration_factor = calibration_factor
        self.calibration_offset = calibration_offset
        self.curve = np.array(curve,dtype=float)
        self.unit = unit

    # Get coil current(s) from magnet strength(s)
    def get_currents(self,strengths:np.array) -> np.array:
        print(strengths)
        return np.array([strengths[0]*self.calibration_factor])

    # Get magnet strength(s) from coil current(s)
    def get_strengths(self,strengths:np.array) -> np.array:
        pass

    def __repr__(self):
        return "%s(calibration_factor=%f, calibration_offset=%f, curve[%d], unit=%s)" % (
            self.__class__.__name__, self.calibration_factor, self.calibration_offset, len(self.curve), self.unit)

def factory_constructor(config: dict) -> LinearUnitConv:
   """Construct a Linear unit conversion object from Yaml config file"""
   return LinearUnitConv(**config)

