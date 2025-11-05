from ..common.element import Element, ElementConfigModel
from ..common.abstract import ReadFloatArray
from ..control.deviceaccess import DeviceAccess

from typing import Self
from pydantic import ConfigDict

PYAMLCLASS = "BetatronTuneMonitor"

class ConfigModel(ElementConfigModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    tune_h: DeviceAccess
    """Horizontal betatron tune"""
    tune_v: DeviceAccess
    """Vertical betatron tune"""

class BetatronTuneMonitor(Element):
    """
    Class providing access to a betatron tune monitor of a physical or simulated lattice.
    The monitor provides horizontal and vertical betatron tune measurements.
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a BetatronTuneMonitor.
        Parameters
        ----------
        cfg : ConfigModel
            Configuration for the BetatronTuneMonitor, including 
            device access for horizontal and vertical tunes.
        """
        
        super().__init__(cfg.name)
        self._cfg = cfg
        self.__tune = None

    @property
    def tune(self) -> ReadFloatArray:
        self.check_peer()
        return self.__tune

    def attach(self, peer, betatron_tune: ReadFloatArray) -> Self:
        obj = self.__class__(self._cfg)
        obj.__tune = betatron_tune
        obj._peer = peer
        return obj

    def __repr__(self):
       return repr(self._cfg).replace("ConfigModel(",self.__class__.__name__ + "(peer='" + self.get_peer() + "', ")

