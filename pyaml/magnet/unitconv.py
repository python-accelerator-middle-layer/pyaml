from abc import ABCMeta, abstractmethod
from pydantic import BaseModel
import numpy as np
from typing import Any

class UnitConv(BaseModel):
    """
    Abstract class providing strength to coil current conversion and access to underlying power supplies
    """

    @abstractmethod
    def compute_currents(self, strengths: np.array) -> np.array:
        """Compute coil current(s) from magnet strength(s)"""
        pass

    @abstractmethod
    def compute_strengths(self, currents: np.array) -> np.array:
        """Compute magnet strength(s) from coil current(s)"""
        pass

    @abstractmethod
    def get_strength_units(self) -> list[str]:
        """Get strength units"""
        pass

    @abstractmethod
    def get_current_units(self) -> list[str]:
        """Get current units"""
        pass

    @abstractmethod
    def read_currents(self) -> np.array:
        """Get power supply current setpoint(s) from control system"""
        pass

    @abstractmethod
    def readback_currents(self) -> np.array:
        """Get power supply current(s) from control system"""
        pass

    @abstractmethod
    def send_currents(self, currents: np.array):
        """Send power supply current(s) to control system"""
        pass

    @abstractmethod
    def set_magnet_rigidity(self, brho: np.double):
        """Set magnet rigidity"""
        pass
