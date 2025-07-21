from pyaml.control import abstract
from pyaml.magnet.unitconv import UnitConv
import numpy as np

#------------------------------------------------------------------------------

class RWCurrentScalar(abstract.ReadFloatScalar):
    """
    Class providing read write access to a magnet current (scalar value) of a control system
    """
    def __init__(self, unitconv:UnitConv):
        self.unitconv = unitconv

    def get(self) -> float:
        return self.unitconv.read_currents()[0]
    
    def set(self, value:float):
        self.unitconv.send_currents([value])
        
    def unit(self) -> str:
        return self.unitconv.get_current_units()[0]
    
#------------------------------------------------------------------------------

class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a strength (scalar value) to a control system
    """

    def __init__(self, unitconv:UnitConv):
        self.unitconv = unitconv
        self.src = None

    # Gets the value
    def get(self) -> float:
        currents = self.unitconv.read_currents()
        return self.unitconv.compute_strengths(currents)[0]

    # Sets the value
    def set(self, value:float):
        current = self.unitconv.compute_currents([value])
        self.unitconv.send_currents(current)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.unitconv.get_strength_units()[0]

#------------------------------------------------------------------------------

class RWCurrentArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a magnet current array of a control system
    """
    def __init__(self, unitconv:UnitConv):
        self.unitconv = unitconv

    # Gets the value
    def get(self) -> np.array:
        return self.unitconv.read_currents()

    # Sets the value
    def set(self, value:np.array) -> np.array:
        self.unitconv.send_currents(value)
        
    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        pass

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.unitconv.get_current_units()

#------------------------------------------------------------------------------

class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a magnet strength array of a control system
    """
    def __init__(self, unitconv:UnitConv):
        self.unitconv = unitconv

    # Gets the value
    def get(self) -> np.array:
        r = self.unitconv.read_currents()
        str = self.unitconv.compute_strengths(r)        
        return str

    # Sets the value
    def set(self, value:np.array) -> np.array:
        cur = self.unitconv.compute_currents(value)
        self.unitconv.send_currents(cur)
        
    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        pass

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.unitconv.get_strength_units()




