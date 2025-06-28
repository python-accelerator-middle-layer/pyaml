import numpy as np
from pyaml.magnet.UnitConv import UnitConv
from pyaml.configuration.Factory import validate
from pyaml.control.Device import Device

"""
Class example proving manget current/strength conversion
"""
class ExternalUnitConv(UnitConv):

    @validate
    def __init__(self, powersupply:Device, id:Device, param: str = None):
        print("ExternalUnitConv:\n  powersupply:%s\n  id:%s\n  param:%s" 
              % (powersupply.setpoint,id.setpoint,param))

    # Get coil current(s) from magnet strength(s)
    def get_currents(self,strengths:np.array) -> np.array:
        print("ExternalUnitConv.get_currents(%f)"%strengths[0])
        return np.array([strengths[0]*1.5])

    # Get magnet strength(s) from coil current(s)
    def get_strengths(self,currents:np.array) -> np.array:
        print("ExternalUnitConv.get_strengths(%f)"%currents[0])
        return np.array([currents[0]/1.5])

    # Set magnet rigidity
    def set_magnet_rigidity(self,brho:np.double):
        pass

def factory_constructor(config: dict) -> ExternalUnitConv:
   """Construct an ExternalUnitConv object from Yaml config file"""
   return ExternalUnitConv(**config)

