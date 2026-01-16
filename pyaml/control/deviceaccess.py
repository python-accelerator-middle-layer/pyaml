from abc import ABCMeta, abstractmethod

# TODO: correctly type value


class DeviceAccess(metaclass=ABCMeta):
    """
    Abstract class providing access to a control system variable
    """

    @abstractmethod
    def name(self) -> str:
        """Return the name of the variable"""
        pass

    @abstractmethod
    def measure_name(self) -> str:
        """Return the name of the measure"""
        pass

    @abstractmethod
    def set(self, value):
        """Write a control system device variable (i.e. a power supply current)"""
        pass

    @abstractmethod
    def set_and_wait(self, value):
        """Write a control system device variable (i.e. a power supply current)"""
        pass

    @abstractmethod
    def get(self):
        """Return the setpoint(s) of a control system device variable"""
        pass

    @abstractmethod
    def readback(self):
        """Return the measured variable"""
        pass

    @abstractmethod
    def unit(self) -> str:
        """Return the variable unit"""
        pass

    @abstractmethod
    def get_range(self) -> list[float]:
        pass

    @abstractmethod
    def check_device_availability(self) -> bool:
        pass

