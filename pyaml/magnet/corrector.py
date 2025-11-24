from .magnet import Magnet
from ..common import abstract
import numpy as np

class RWCorrectorAngle(abstract.ReadWriteFloatScalar):
    """
    Set the angle of a horizontal or vertical corrector.
    KickAngle sign convention is defined the accelerator level.
    """
    def __init__(self, corr:Magnet):
        self._mag = corr

    def get(self) -> float:
        return np.arctan(self._mag.strength.get())
    
    def set(self,value:float):
        self._mag.strength.set( np.tan(value) )

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return "rad"
