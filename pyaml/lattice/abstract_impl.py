from pyaml.control import abstract
from pyaml.magnet.unitconv import UnitConv
from .polynom_info import PolynomInfo
import numpy as np
import at

# TODO handle serialized magnets

#------------------------------------------------------------------------------

class RWCurrentScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read access to a manget current (scalar value) of a simulator
    Current is converted from Strenght using UnitConv
    """

    def __init__(self, elements:list[at.Element], poly:PolynomInfo, unitconv:UnitConv):
        self.unitconv = unitconv
        self.elements = elements
        self.poly = elements[0].__getattribute__(poly.attName)
        self.polyIdx = poly.index

    def get(self) -> float:
        s = self.poly[self.polyIdx] * self.elements[0].Length
        return self.unitconv.compute_currents([s])[0]
    
    def set(self,value:float):
        s = self.unitconv.compute_strengths([value])[0]
        self.poly[self.polyIdx] = s / self.elements[0].Length

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return self.unitconv.get_current_units()[0]
    
#------------------------------------------------------------------------------

class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a strength (scalar value) of a simulator
    """

    def __init__(self, elements:list[at.Element], poly:PolynomInfo):
        self.elements = elements
        self.poly = elements[0].__getattribute__(poly.attName)
        self.polyIdx = poly.index

    # Gets the value
    def get(self) -> float:
        return self.poly[self.polyIdx] * self.elements[0].Length

    # Sets the value
    def set(self, value:float):
        self.poly[self.polyIdx] = value / self.elements[0].Length

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.unitconv.get_strength_units()[0]

#------------------------------------------------------------------------------

class RWCurrenthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a current (array) of a simulator
    """

    def __init__(self, elements:list[at.Element], poly:list[PolynomInfo], unitconv:UnitConv):
        self.elements = elements
        self.poly = []
        self.polyIdx = []
        self.unitconv = unitconv
        for p in poly:
            self.poly.append[elements[0].__getattribute__(p.attName)]
            self.polyIdx.append(p.index)

    # Gets the value
    def get(self) -> np.array:  
        nbStrength = len(self.poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            s[i] = self.poly[i][self.polyIdx[i]] * self.elements[0].Length
        return self.unitconv.compute_currents([s])

    # Sets the value
    def set(self, value:np.array):
        nbStrength = len(self.poly)
        s = self.unitconv.compute_strengths(value)
        for i in range(nbStrength):
            self.poly[i][self.polyIdx[i]] = s[i] / self.elements[0].Length

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.unitconv.get_current_units()

#------------------------------------------------------------------------------

class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a strength (array) of a simulator
    """

    def __init__(self, elements:list[at.Element], poly:list[PolynomInfo]):
        self.elements = elements
        self.poly = []
        self.polyIdx = []
        for p in poly:
            self.poly.append[elements[0].__getattribute__(p.attName)]
            self.polyIdx.append(p.index)

    # Gets the value
    def get(self) -> np.array:  
        nbStrength = len(self.poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            s[i] = self.poly[i][self.polyIdx[i]] * self.elements[0].Length
        return s

    # Sets the value
    def set(self, value:np.array):
        nbStrength = len(self.poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            self.poly[i][self.polyIdx[i]] = value / self.elements[0].Length

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.unitconv.get_strength_units()[0]

