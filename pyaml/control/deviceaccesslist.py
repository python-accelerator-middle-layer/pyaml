"""
Abstract collection interface for control-system devices.

Backends implement :class:`DeviceAccessList` to expose ordered groups of
device variables with bulk read, write, range, unit, and availability support.
"""

from abc import ABCMeta, abstractmethod

import numpy as np
import numpy.typing as npt

from .deviceaccess import DeviceAccess


class DeviceAccessList(metaclass=ABCMeta):
    """
    Define ordered bulk access to control-system device variables.

    The internal representation is backend-dependent.  Implementations expose
    devices in a stable order so array values correspond to the same order for
    reads, writes, readbacks, and ranges.

    Methods
    -------
    add_devices(devices)
        Add one device or a list of devices to the collection.
    get_device_at(index)
        Return the device at a zero-based index.
    len()
        Return the number of devices in the collection.
    set(value)
        Write one setpoint for each device in collection order.
    set_and_wait(value)
        Write setpoints and wait for all devices to reach them.
    get()
        Return all current setpoints in collection order.
    readback()
        Return the latest measured values in collection order.
    unit()
        Return the unit or units associated with the devices.
    get_range()
        Get the valid range for the device variables.
    check_device_availability()
        Check if all devices in the list are available and accessible.
    """

    @abstractmethod
    def add_devices(self, devices: DeviceAccess | list[DeviceAccess]):
        """
        Add one device or a list of devices to the collection.

        Parameters
        ----------
        devices : DeviceAccess | list[DeviceAccess]
            Device or devices to append, in the order they should be read.
        """
        pass

    @abstractmethod
    def get_device_at(self, index: int) -> DeviceAccess:
        """
        Return the device at a zero-based index.

        Parameters
        ----------
        index : int
            Position of the requested device.

        Returns
        -------
        DeviceAccess
            Device at ``index``.
        """
        pass

    @abstractmethod
    def len(self) -> int:
        """Return the number of devices in the collection."""
        pass

    @abstractmethod
    def set(self, value: npt.NDArray[np.float64]):
        """
        Write one setpoint for each device in collection order.

        Parameters
        ----------
        value : numpy.typing.NDArray[numpy.float64]
            Setpoints ordered to match the devices.
        """
        pass

    @abstractmethod
    def set_and_wait(self, value: npt.NDArray[np.float64]):
        """
        Write setpoints and wait for all devices to reach them.

        Parameters
        ----------
        value : numpy.typing.NDArray[numpy.float64]
            Setpoints ordered to match the devices.
        """
        pass

    @abstractmethod
    def get(self) -> npt.NDArray[np.float64]:
        """Return all current setpoints in collection order."""
        pass

    @abstractmethod
    def readback(self) -> np.array:
        """
        Return the latest measured values in collection order.

        Returns
        -------
        numpy.ndarray
            Readback values corresponding to the devices returned by
            :meth:`get_device_at` at each index.
        """
        pass

    @abstractmethod
    def unit(self) -> str:
        """Return the unit or units associated with the devices."""
        pass

    @abstractmethod
    def get_range(self) -> list[float]:
        """
        Get the valid range for the device variables.

        Returns
        -------
        list[float]
            Flat list containing ``[min0, max0, min1, max1, ...]``.
            ``None`` may represent an unbounded limit.
        """
        pass

    @abstractmethod
    def check_device_availability(self) -> bool:
        """
        Check if all devices in the list are available and accessible.

        Returns
        -------
        bool
            ``True`` only if every device is available and accessible.
        """
        pass

    # Immutable list implementation

    def __getitem__(self, index):
        """
        Return the device at ``index``.

        Parameters
        ----------
        index : object
            Integer index of the requested device.

        Returns
        -------
        DeviceAccess
            Device selected by ``index``.
        """
        return self.get_device_at(index)

    def __len__(self):
        """Return the number of devices in the collection."""
        return self.len()

    def __iter__(self):
        """Return an iterator over the devices in collection order."""
        self._iter_pos = 0
        return self

    def __next__(self):
        """
        Return the next device during iteration.

        Raises
        ------
        StopIteration
            When all devices have been visited.
        """
        if self._iter_pos < len(self._items):
            self._iter_pos += 1
            return self._items[self._iter_pos - 1]
        else:
            raise StopIteration
