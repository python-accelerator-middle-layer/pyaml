import numpy as np
from numpy import typing as npt
from pydantic import BaseModel

import pyaml
from pyaml.control.deviceaccess import DeviceAccess
from pyaml.control.deviceaccesslist import DeviceAccessList

from .attribute import Attribute
from .attribute import ConfigModel as AttributeConfigModel

PYAMLCLASS: str = "MultiAttribute"

LAST_NB_WRITTEN = 0


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
    def __init__(self, cfg: ConfigModel = None):
        super().__init__()
        self._cfg = cfg
        if cfg.attributes:
            for name in cfg.attributes:
                self.add_devices(Attribute(AttributeConfigModel(name, cfg.unit)))

    def add_devices(self, devices: DeviceAccess | list[DeviceAccess]):
        if isinstance(devices, list):
            for device in devices:
                if not isinstance(device, Attribute):
                    raise pyaml.PyAMLException(
                        f"""All devices must be instances of Attribute
                        (tango.pyaml.attribute) but got
                        ({device.__class__.__name__})"""
                    )
            super().extend(devices)
        else:
            if not isinstance(devices, Attribute):
                raise pyaml.PyAMLException(
                    f"""Device must be an instance of Attribute
                    (tango.pyaml.attribute) but got
                    ({devices.__class__.__name__})"""
                )
            super().append(devices)

    def get_devices(self) -> DeviceAccess | list[DeviceAccess]:
        if len(self) == 1:
            return self[0]
        else:
            return self

    def set(self, value: npt.NDArray[np.float64]):
        print(f"MultiAttribute.set({len(value)} values)")
        global LAST_NB_WRITTEN
        LAST_NB_WRITTEN += len(value)
        for idx, a in enumerate(self):
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

    def get_last_nb_written(self) -> int:
        return self.__last_nb_written
