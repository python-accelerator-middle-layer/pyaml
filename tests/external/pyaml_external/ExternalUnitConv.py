import numpy as np
from pyaml.magnet.UnitConv import UnitConv
from pyaml.configuration.Factory import validate
from pyaml.control.Device import Device

"""
Class that handle manget current/strength conversion using linear interpolation for a single function magnet
"""
class ExternalUnitConv(UnitConv):

    @validate
    def __init__(self, powersupply:Device, param: str = None):
        print("ExternalUnitConv: Device + " + powersupply.setpoint + ", Param:" + param)

    # Get coil current(s) from magnet strength(s)
    def get_currents(self,strengths:np.array) -> np.array:
        print("In get_currents")
        return np.array([strengths[0]*1.5])

    # Get magnet strength(s) from coil current(s)
    def get_strengths(self,strengths:np.array) -> np.array:
        print("In get_strengths")

    # Set magnet rigidity
    def set_magnet_rigidity(self,brho:np.double):
        pass

def factory_constructor(config: dict) -> ExternalUnitConv:
   """Construct a Linear unit conversion object from Yaml config file"""
   return ExternalUnitConv(**config)

