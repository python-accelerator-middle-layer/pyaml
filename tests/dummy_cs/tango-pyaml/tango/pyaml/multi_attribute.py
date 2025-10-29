import pyaml
from numpy import typing as npt
import numpy as np
from pyaml.control.deviceaccess import DeviceAccess
from pydantic import BaseModel

from pyaml.control.deviceaccesslist import DeviceAccessList
from .attribute import Attribute
from .attribute import ConfigModel as AttributeConfigModel

PYAMLCLASS : str = "MultiAttribute"


class ConfigModel(BaseModel):
    """
    Configuration model for a list of DeviceAccess.

    Attributes
    ----------
    attributes : list of str
        List of Tango attribute paths.
    name : str, optional
        Group name.
    unit : str, optional
        Unit of the attributes.
    """
    attributes: list[str] = []
    name: str = ""

class MultiAttribute(DeviceAccessList):

    def __init__(self, cfg:ConfigModel=None):
        super().__init__()
        self._cfg = cfg
        if cfg.attributes:
            for name in cfg.attributes:
                self.add_devices(Attribute(AttributeConfigModel(name,cfg.unit)))

    def add_devices(self, devices: DeviceAccess | list[DeviceAccess]):
        if isinstance(devices, list):
            if any([not isinstance(device, Attribute) for device in devices]):
                raise pyaml.PyAMLException("All devices must be instances of Attribute (tango.pyaml.attribute).")
            super().extend(devices)
        else:
            if not isinstance(devices, Attribute):
                raise pyaml.PyAMLException("Device must be an instance of Attribute (tango.pyaml.attribute).")
            super().append(devices)

    def get_devices(self) -> DeviceAccess | list[DeviceAccess]:
        if len(self)==1:
            return self[0]
        else:
            return self

    def set(self, value: npt.NDArray[np.float64]):
        print(f"MultiAttribute.set({len(value)} values)")
        for idx,a in enumerate(self):
            a.set(value[idx])

    def set_and_wait(self, value: npt.NDArray[np.float64]):
        pass

    def get(self) -> npt.NDArray[np.float64]:
        print(f"MultiAttribute.get({len(self)} values)")
        return [a.get() for a in self]

    def readback(self) -> np.array:
        return []

    def unit(self) -> list[str]:
        return [a.unit() for a in self]
