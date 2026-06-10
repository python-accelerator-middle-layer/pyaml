# This example show a minimal Tango control system implementation

import logging

import tango
from pydantic import BaseModel

from pyaml.control.controlsystem import ControlSystemAdapter
from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS: str = "MyControlSystem"

# ---------------------- ControlSystem configuration model -----------------------


class ConfigModel(BaseModel):
    """
    Configuration model for an OA Control System.

    Attributes
    ----------
    name : str
        Name of the control system.
    prefix : str
        Prefix added to the to name passed to get_device()
    """

    name: str
    prefix: str = ""


# ---------------------- Hardware access interface -------------------------------


class MyDevice(DeviceAccess):
    def __init__(self, name: str):
        self._name = self.name
        self._proxy = tango.AttributeProxy(name)
        att_config = self._proxy.get_config()
        self._iswrittable = att_config.writable in [
            tango.AttrWriteType.READ_WRITE,
            tango.AttrWriteType.WRITE,
            tango.AttrWriteType.READ_WITH_WRITE,
        ]
        self._unit = att_config.unit
        try:
            min = float(att_config.min_value)
            max = float(att_config.max_value)
            self._range = [min, max]
        except Exception:
            self._range = [None, None]

    def name(self) -> str:
        """Return the name of the variable"""
        return self._name

    def measure_name(self) -> str:
        """Return the name of the measure"""
        return self._name

    def set(self, value):
        """Write a control system device variable (i.e. a power supply current)"""
        self._proxy.write(value)

    def set_and_wait(self, value):
        """Write a control system device variable (i.e. a power supply current)"""
        pass

    def get(self):
        """Return the setpoint(s) of a control system device variable"""
        if self._iswrittable:
            return self._proxy.read().w_value
        else:
            return self._proxy.read().value

    def readback(self):
        """Return the measured variable"""
        return self._proxy.read().value

    def unit(self) -> str:
        """Return the variable unit"""
        return self._unit

    def get_range(self) -> list[float]:
        """
        Get the valid range for the device variable.

        Returns
        -------
        list[float]
            List containing [min, max] values
        """
        return self._range

    def check_device_availability(self) -> bool:
        """
        Check if the device is available and accessible.

        Returns
        -------
        bool
            True if device is available, False otherwise
        """
        return self._proxy.ping()


# ---------------------- The control system class -------------------------------


class MyControlSystem(ControlSystemAdapter):
    def __init__(self, cfg: ConfigModel):
        super().__init__()
        self._cfg = cfg

    def get_device(self, ref: str | BaseModel | None) -> DeviceAccess | None:
        if ref is None:
            return None
        return MyDevice(self._cfg.prefix + ref)

    def name(self) -> str:
        return self._cfg.name

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
