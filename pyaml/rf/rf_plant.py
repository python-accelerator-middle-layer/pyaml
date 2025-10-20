import numpy as np
from pydantic import BaseModel,ConfigDict
try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier

from .rf_transmitter import RFTransmitter
from .. import PyAMLException
from ..control.deviceaccess import DeviceAccess
from ..lattice.element import Element,ElementConfigModel
from ..control import abstract

# Define the main class name for this module
PYAMLCLASS = "RFPlant"

class ConfigModel(ElementConfigModel):

    masterclock: DeviceAccess|None = None
    """Device to apply main RF frequency"""
    transmitters: list[RFTransmitter]|None = None
    """List of RF trasnmitters"""

class RFPlant(Element):

    """
    Main RF object
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg.name)
        self._cfg = cfg
        self.__frequency = None
        self.__allcav = []
        self.__allharmonics = []
        for c in cfg.transmitters:
            self.__allcav.extend(c._cfg.cavities)
            self.__allharmonics.extend(c._cfg.harmonics)

    @property
    def frequency(self) -> abstract.ReadWriteFloatScalar:
        if self.__frequency is None:
            raise PyAMLException(f"{str(self)} has no masterclock device defined")
        return self.__frequency

    def attach(self, frequency: abstract.ReadWriteFloatScalar) -> Self:
        # Attach frequency attribute and returns a new reference
        obj = self.__class__(self._cfg)
        obj.__frequency = frequency
        return obj
