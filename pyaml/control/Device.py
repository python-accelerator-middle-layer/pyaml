"""
Class providing access to a device of the control system
"""

import numpy as np

from ..configuration.models import ConfigBase


class Config(ConfigBase):
    setpoint: str
    readback: str
    unit: str


class Device(object):
    def __init__(self, cfg: Config):
        self._cfg = cfg

        self.setpoint = cfg.setpoint
        self.readback = cfg.readback
        self.unit = cfg.unit
        self.cache = 0.0  # Debugging purpose (to be removed)

    # Sets the value
    def set(self, value: float):
        print("%s: set %f" % (self.setpoint, value))
        self.cache = value

    # Get the setpoint
    def get(self):
        return self.cache
