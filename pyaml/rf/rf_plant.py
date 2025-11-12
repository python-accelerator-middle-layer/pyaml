import numpy as np
from pydantic import BaseModel,ConfigDict
try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier

from .rf_transmitter import RFTransmitter
from .. import PyAMLException
from ..control.deviceaccess import DeviceAccess
from ..common.element import Element,ElementConfigModel
from ..common import abstract

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
        self.__voltage = None

    @property
    def frequency(self) -> abstract.ReadWriteFloatScalar:
        if self.__frequency is None:
            raise PyAMLException(f"{str(self)} has no masterclock device defined")
        return self.__frequency

    @property
    def voltage(self) -> abstract.ReadWriteFloatScalar:
        if self.__voltage is None:
            raise PyAMLException(f"{str(self)} has no trasmitter device defined")
        return self.__voltage

    def attach(self, peer, frequency: abstract.ReadWriteFloatScalar, voltage: abstract.ReadWriteFloatScalar) -> Self:
        # Attach frequency attribute and returns a new reference
        obj = self.__class__(self._cfg)
        obj.__frequency = frequency
        obj.__voltage = voltage
        obj._peer = peer
        return obj
    
class RWTotalVoltage(abstract.ReadWriteFloatScalar):

    def __init__(self, transmitters: list[RFTransmitter]):
        """
        Construct a RWTotalVoltage setter

        Parameters
        ----------
        transmitters : list[RFTransmitter]
            List of attached transmitters
        """
        self.__trans = transmitters

    def get(self) -> float:
        sum = 0
        # Count only fundamental harmonic
        for t in self.__trans:
            if(t._cfg.harmonic==1.):
                sum += t.voltage.get()
        return sum
    
    def set(self,value:float):
        # Assume that sum of transmitter (fundamental harmonic) distribution is 1
        for t in self.__trans:
            if(t._cfg.harmonic==1.):
                v = value * t._cfg.distribution
                t.voltage.set(v)

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return self.__trans[0]._cfg.phase.unit()

    


