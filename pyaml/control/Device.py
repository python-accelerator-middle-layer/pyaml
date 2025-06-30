"""
Class providing access to a device of the control system
"""
import numpy as np

class Device(object):
    def __init__(self,setpoint:str,readback:str,unit:str):
        self.setpoint = setpoint
        self.readback = readback
        self.unit = unit
        self.cache = 0.0 # Debugging purpose (to be removed)

    # Sets the value
    def set(self,value:float):
        print("%s: set %f" % (self.setpoint,value))
        self.cache = value

    # Get the setpoint
    def get(self):
        return self.cache

def factory_constructor(config: dict) -> Device:
   """Construct a Device from Yaml config file"""
   return Device(**config)
