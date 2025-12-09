from abc import ABCMeta, abstractmethod

import numpy as np
from numpy.typing import NDArray

from ..control.deviceaccess import DeviceAccess


class BPMModel(metaclass=ABCMeta):
    """
    Abstract class providing interface to accessing BPM positions, offsets,
    tilts.
    """

    @abstractmethod
    def get_pos_devices(self) -> list[DeviceAccess]:
        """
        Get device handles used for position reading

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        pass

    @abstractmethod
    def get_tilt_device(self) -> DeviceAccess | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        pass

    @abstractmethod
    def get_offset_devices(self) -> list[DeviceAccess]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            Array of DeviceAcess
        """
        pass
