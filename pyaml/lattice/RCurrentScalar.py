from pyaml.control import Abstract
from pyaml.magnet.UnitConv import UnitConv
import numpy as np
import at

class RCurrentScalar(Abstract.ReadFloatScalar):
    """
    Class providing read access to a current (scalar value) of a control system
    """
    def __init__(self, unitconv:UnitConv):
        self.unitconv = unitconv

    # Gets the value
    def get(self) -> np.double:
        if self.unitconv is None:
            return np.nan
        else:
            return self.unitconv.read_currents()[0]
        
    # Gets the unit of the value
    def unit(self) -> str:
        return self.unitconv.get_current_units()[0]




