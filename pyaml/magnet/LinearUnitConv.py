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

        self.calibration_factor = calibration_factor
        self.calibration_offset = calibration_offset
        self.curve = curve.get_curve()
        self.unit = unit
        self.brho = np.NaN

    # Get coil current(s) from magnet strength(s)
    def get_currents(self,strengths:np.array) -> np.array:
        print(strengths)
        return np.array([strengths[0]*self.calibration_factor])

    # Get magnet strength(s) from coil current(s)
    def get_strengths(self,strengths:np.array) -> np.array:
        pass

    # Set magnet rigidity
    def set_magnet_rigidity(self,brho:np.double):
        self.brho = brho

    def __repr__(self):
        return "%s(calibration_factor=%f, calibration_offset=%f, curve[%d], unit=%s)" % (
            self.__class__.__name__, self.calibration_factor, self.calibration_offset, len(self.curve), self.unit)

def factory_constructor(config: dict) -> LinearUnitConv:
   """Construct a Linear unit conversion object from Yaml config file"""
   return LinearUnitConv(**config)

