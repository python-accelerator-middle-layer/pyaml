from typing import Literal

from pydantic import BaseModel

from ..deviceaccess import DeviceAccess
from . import arun
from .types import (
    EpicsConfigR, EpicsConfigW, EpicsConfigRW,
    TangoConfigR, TangoConfigW, TangoConfigRW,
    ControlSysConfig,
)
from .pool import global_pool


class ConfigModel(BaseModel):
    cs_config: ControlSysConfig
    unit: str = ""


class FloatSignalContainer(DeviceAccess):
    """
    Class that implements a PyAML Float Signal using ophyd_async Signals.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self._unit = cfg.unit
        cs_cfg = cfg.cs_config
        if isinstance(cs_cfg, (EpicsConfigRW, EpicsConfigR)):
            self._cs_name = "epics"
        elif isinstance(cs_cfg, (TangoConfigRW, TangoConfigR)):
            self._cs_name = "tango"
        else:
            raise ValueError("Unsupported control system config type")
        self._readable: bool = isinstance(cs_cfg, (EpicsConfigRW, EpicsConfigR,
                                                  TangoConfigRW, TangoConfigR))
        self._writable: bool = isinstance(cs_cfg, (EpicsConfigRW, EpicsConfigW,
                                                  TangoConfigRW, TangoConfigW))

        self.SP, self.RB = global_pool.get(self._cs_name, cfg.cs_config)


    def name(self) -> str:
        """
        Return the name of the signal.
        """
        return self._signal.name

    def measure_name(self) -> str:
        """
        Return the short attribute name (last component).

        Returns
        -------
        str
            The attribute name (e.g., 'current').
        """

        if self._cs_name == 'epics':
            return self._cfg.cs_config.read_pvname
        elif self._cs_name == 'tango':
            return self._cfg.cs_config.read_attr
        else:
            raise ValueError(f"Unsupported control system: {self._cs_name}")


    def unit(self) -> str:
        """
        Return the unit of the attribute.

        Returns
        -------
        str
            The unit string.
        """
        return self._unit

    def get(self) -> float:
        """
        Get the last written value of the attribute.

        Returns
        -------
        float
            The last written value.

        """
        # return arun(self.SP.async_get())
        return self.SP.get()


    def readback(self) -> float:
        """
        Return the readback value with metadata.

        Returns
        -------
        Value
            The readback value including quality and timestamp.

        """
        # return arun(self.RB.async_get())
        return self.RB.get()

    def set(self, value: float):
        """
        Write a value asynchronously to the Tango attribute.

        Parameters
        ----------
        value : float
            Value to write to the attribute.

        """
        # return arun(self.SP.async_set(value))
        return self.SP.set(value)

    def set_and_wait(self, value: float):
        """
        Write a value synchronously to the Tango attribute.

        Parameters
        ----------
        value : float
            Value to write to the attribute.

        """
        # arun(self.SP.async_set_and_wait(value))
        self.SP.set_and_wait(value)

