from abc import ABCMeta, abstractmethod
from pathlib import Path

import numpy as np

from ..configuration.models import ConfigBase


class Config(ConfigBase):
    unit: str | None = None
    filepath: str | Path | None = None


class UnitConv(metaclass=ABCMeta):
    """
    Abstract class providing strength to coil current conversion and access to underlying power supplies
    """

    # Compute coil current(s) from magnet strength(s)
    @abstractmethod
    def compute_currents(self, strengths: np.array) -> np.array:
        pass

    # Compute magnet strength(s) from coil current(s)
    @abstractmethod
    def compute_strengths(self, currents: np.array) -> np.array:
        pass

    # Get strength units
    @abstractmethod
    def get_strengths_units(self) -> list[str]:
        pass

    # Get current units
    @abstractmethod
    def get_current_units(self) -> list[str]:
        pass

    # Get power supply current setpoint(s) from control system
    @abstractmethod
    def read_currents(self) -> np.array:
        pass

    # Get power supply current(s) from control system
    @abstractmethod
    def readback_currents(self) -> np.array:
        pass

    # Send power supply current(s) to control system
    @abstractmethod
    def send_currents(self, currents: np.array):
        pass

    # Set magnet rigidity
    @abstractmethod
    def set_magnet_rigidity(self, brho: np.double):
        pass
