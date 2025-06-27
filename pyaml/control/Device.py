"""
Class providing access to a device of the control system
"""

class Device(object):
    def __init__(self,setpoint:str,readback:str,unit:str):
        self.setpoint = setpoint
        self.readback = readback
        self.unit = unit
        pass

def factory_constructor(config: dict) -> Device:
   """Construct a Device from Yaml config file"""
   return Device(**config)
