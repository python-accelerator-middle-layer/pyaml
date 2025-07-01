import numpy as np
from pyaml.magnet.UnitConv import UnitConv
from pyaml.configuration.Factory import validate
from pyaml.control.DeviceAccess import Device

"""
Class example proving manget current/strength conversion
"""
class ExternalUnitConv(UnitConv):

    # The constructor signature indicates what should be inside the assocaited 
    # configuration file. Parameters with a default value are optional.
    # The validate decorator check that input types are correct
    @validate
    def __init__(self, powersupply:Device, id:Device, param:str = None):
        print("ExternalUnitConv:\n  powersupply:%s\n  id:%s\n  param:%s" 
              % (powersupply.setpoint,id.setpoint,param))
        self.powersupply = powersupply
        id.set(10) # Mimic a default value for the gap
        self.id = id

    # Implementation of the UnitConv abstract class

    # Get coil current(s) from magnet strength(s)
    def compute_currents(self,strengths:np.array) -> np.array:
        print("ExternalUnitConv.compute_currents(%f)" % (strengths[0]))
        gap = self.id.get()
        return np.array([strengths[0]*gap])

    # Get magnet strength(s) from coil current(s)
    def compute_strengths(self,currents:np.array) -> np.array:
        print("ExternalUnitConv.compute_strengths(%f)" % (currents[0]))
        gap = self.id.get()
        return np.array([currents[0]/gap])

    # Get strength units
    def get_strengths_units(self) -> list[str]:
        return["rad"]

    # Get current units
    def get_current_units(self) -> list[str]:
        return["A"]

    # Get power supply current setpoint(s) from control system
    def read_currents(self) -> np.array:
        return self.powersupply.get()

    # Get power supply current(s) from control system
    def readback_currents(self) -> np.array:
        pass

    # Send power supply current(s) to control system
    def send_currents(self,currents:np.array):
        self.powersupply.set(currents)
        pass

    # Set magnet rigidity
    def set_magnet_rigidity(self,brho:np.double):
        pass

def factory_constructor(config: dict) -> ExternalUnitConv:
   """Construct an ExternalUnitConv object from Yaml config file"""
   return ExternalUnitConv(**config)

