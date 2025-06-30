"""
Class providing access to a device of the control system
"""
from pydantic import BaseModel
from typing import Optional

class Device(BaseModel):

    setpoint : str
    readback : Optional[str] = None
    unit : Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._cache = 0.0 # Debugging purpose (to be removed)

    # Sets the value
    def set(self,value:float):
        print("%s: set %f" % (self.setpoint,value))
        self._cache = value

    # Get the setpoint
    def get(self):
        return self.cache

def factory_constructor(config: dict) -> Device:
   """Construct a Device from Yaml config file"""
   return Device(**config)
