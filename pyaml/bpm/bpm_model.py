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
    def get_pos_devices(self) -> list[DeviceAccess | None]:
        """
        Get device handles used for position reading

        Returns
        -------
        list[DeviceAccess]
            h and v position devices
        """
        pass

    @abstractmethod
    def get_tilt_device(self) -> DeviceAccess | None:
        """
        Get device handle used for tilt access

        Returns
        -------
        list[DeviceAccess]
            tilt device
        """
        pass

    @abstractmethod
    def get_offset_devices(self) -> list[DeviceAccess | None]:
        """
        Get device handles used for offset access

        Returns
        -------
        list[DeviceAccess]
            h and v offset devices
        """
        pass

    def x_pos_index(self) -> int | None:
        """
        Returns the index of the horizontal position in
        an array, otherwise a scalar value is expected from the
        corresponding DeviceAccess

        Returns
        -------
        int
            Index in the array, None for a scalar value
        """
        return None

    def y_pos_index(self) -> int | None:
        """
        Returns the index of the veritcal position in
        an array, otherwise a scalar value is expected from the
        corresponding DeviceAccess

        Returns
        -------
        int
            Index in the array, None for a scalar value
        """
        return None

    def is_pos_indexed(self) -> bool:
        """
        Check if position values are indexed (array-based).

        Returns
        -------
        bool
            True if both x and y positions are indexed, False otherwise
        """
        return self.x_pos_index() is not None and self.y_pos_index() is not None

    def tilt_index(self) -> int | None:
        """
        Returns the index of the tilt angle in
        an array, otherwise a scalar value is expected from the
        corresponding DeviceAccess

        Returns
        -------
        int
            Index in the array, None for a scalar value
        """
        return None

    def is_tilt_indexed(self) -> bool:
        """
        Check if tilt value is indexed (array-based).

        Returns
        -------
        bool
            True if tilt is indexed, False otherwise
        """
        return self.tilt_index() is not None

    def x_offset_index(self) -> int | None:
        """
        Returns the index of the horizontal offset in
        an array, otherwise a scalar value is expected from the
        corresponding DeviceAccess

        Returns
        -------
        int
            Index in the array, None for a scalar value
        """
        return None

    def y_offset_index(self) -> int | None:
        """
        Returns the index of the veritcal offset in
        an array, otherwise a scalar value is expected from the
        corresponding DeviceAccess

        Returns
        -------
        int
            Index in the array, None for a scalar value
        """
        return None

    def is_offset_indexed(self) -> bool:
        """
        Check if offset values are indexed (array-based).

        Returns
        -------
        bool
            True if both x and y offsets are indexed, False otherwise
        """
        return self.x_offset_index() is not None and self.y_offset_index() is not None
