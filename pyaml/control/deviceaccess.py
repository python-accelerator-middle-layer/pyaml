"""
Abstract interface for control-system device access.

Backends implement :class:`DeviceAccess` to expose device names, setpoints,
readbacks, units, limits, and availability through a common PyAML interface.
"""

from abc import ABCMeta, abstractmethod

# TODO: correctly type value


class DeviceAccess(metaclass=ABCMeta):
    """
    Define the interface for one control-system device variable.

    Implementations may represent a process variable, power-supply channel,
    measurement channel, or another backend-specific device.  ``get`` and
    ``readback`` distinguish the requested setpoint from the measured value.
    """

    @abstractmethod
    def name(self) -> str:
        """
        Return the backend identifier of the device variable.

        Returns
        -------
        str
            Device or process-variable name.
        """
        pass

    @abstractmethod
    def measure_name(self) -> str:
        """
        Return the identifier of the device's measurement channel.

        Returns
        -------
        str
            Measurement-channel name.
        """
        pass

    @abstractmethod
    def set(self, value):
        """
        Write a new setpoint to the device variable.

        Parameters
        ----------
        value : object
            Backend-compatible value to write.
        """
        pass

    @abstractmethod
    def set_and_wait(self, value):
        """
        Write a setpoint and wait until the device reaches it.

        Parameters
        ----------
        value : object
            Backend-compatible value to write.
        """
        pass

    @abstractmethod
    def get(self):
        """Return the current device setpoint."""
        pass

    @abstractmethod
    def readback(self):
        """
        Return the latest measured value reported by the device.

        Returns
        -------
        object
            Backend-provided readback value, which may differ from the
            commanded setpoint returned by :meth:`get`.
        """
        pass

    @abstractmethod
    def unit(self) -> str:
        """
        Return the physical unit of the device variable.

        Returns
        -------
        str
            Unit label, such as ``"A"`` or ``"Hz"``.
        """
        pass

    @abstractmethod
    def get_range(self) -> list[float]:
        """
        Get the valid range for the device variable.

        Returns
        -------
        list[float]
            Two-element list containing the inclusive minimum and maximum
            values. ``None`` may be used for an unbounded limit.
        """
        pass

    @abstractmethod
    def check_device_availability(self) -> bool:
        """
        Check if the device is available and accessible.

        Returns
        -------
        bool
            ``True`` if the device can be accessed; otherwise ``False``.
        """
        pass
