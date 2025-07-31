from abc import ABCMeta, abstractmethod
import numpy as np

class MagnetModel(metaclass=ABCMeta):
    """
    Abstract class providing strength to coil current conversion and access to underlying power supplies
    """

    @abstractmethod
    def compute_hardware_values(self, strengths: np.array) -> np.array:
        """Compute hardware value(s) from magnet strength(s)"""
        pass

    @abstractmethod
    def compute_strengths(self, hardware_values: np.array) -> np.array:
        """Compute magnet strength(s) from hardware value(s)"""
        pass

    @abstractmethod
    def get_strength_units(self) -> list[str]:
        """Get strength units"""
        pass

    @abstractmethod
    def get_hardware_units(self) -> list[str]:
        """Get hardware units"""
        pass

    @abstractmethod
    def read_hardware_values(self) -> np.array:
        """Get power supply current setpoint(s) from control system"""
        pass

    @abstractmethod
    def readback_hardware_values(self) -> np.array:
        """Get power supply harware value(s) from control system"""
        pass

    @abstractmethod
    def send_harware_values(self, currents: np.array):
        """Send power supply value(s) to control system"""
        pass

    @abstractmethod
    def set_magnet_rigidity(self, brho: np.double):
        """Set magnet rigidity"""
        pass
