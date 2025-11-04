
from ..lattice.element import Element, ElementConfigModel
from ..lattice.abstract_impl import RBetatronTuneArray
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
    def tune(self) -> RBetatronTuneArray:
        return self.__tune

    def attach(self, betatron_tune: RBetatronTuneArray) -> Self:

        obj = self.__class__(self._cfg)
        obj.__tune = betatron_tune
        return obj
        
