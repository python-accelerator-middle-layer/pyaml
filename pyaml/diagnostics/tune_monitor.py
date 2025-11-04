
from pyaml.lattice.element import Element, ElementConfigModel
from pyaml.lattice.abstract_impl import RBetatronTuneArray
from ..control.deviceaccess import DeviceAccess
from typing import Self
from pydantic import ConfigDict
from ..control.deviceaccess import DeviceAccess

PYAMLCLASS = "BetatronTuneMonitor"

class ConfigModel(ElementConfigModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    tune_h: DeviceAccess
    """Horizontal betatron tune"""
    tune_v: DeviceAccess
    """Vertical betatron tune"""

class BetatronTuneMonitor(Element):
    """
    Class providing access to one BPM of a physical or simulated lattice
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a BPM

        Parameters
        ----------
        name : str
            Element name
        model : BetatronTuneMonitorModel
            BetatronTuneMonitorModel
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
        
