from pyaml.control import abstract
from pyaml.magnet.unitconv import UnitConv
import numpy as np
import at

#------------------------------------------------------------------------------

class RCurrentScalar(abstract.ReadFloatScalar):
    """
    Class providing read access to a current (scalar value) of a control system
    """
    def __init__(self, unitconv:UnitConv):
        self.unitconv = unitconv

    def get(self) -> float:
        if self.unitconv is None:
            return np.nan
        else:
            return self.unitconv.read_currents()[0]
        
    def unit(self) -> str:
        return self.unitconv.get_current_units()[0]

#------------------------------------------------------------------------------

class RWMapper(abstract.ReadWriteFloatScalar):
    """
    Class mapping a scalar to an element of an array
    """
    def __init__(self, bind, idx:int):
        self.bind = bind
        self.idx = idx

    # Gets the value
    def get(self) -> float:
        return self.bind.get()[self.idx]

    # Sets the value
    def set(self, value:float):
        arr = self.bind.get()
        arr[self.idx] = value
        self.bind.set(arr)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")

#------------------------------------------------------------------------------

class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a strength (array) of a simulator or to a control system
    """

    def __init__(self, elementName:str,unitconv:UnitConv,nbMultipole:int):
        self.unitconv = unitconv
        self.elementName = elementName

    # Gets the value
    def get(self) -> np.array:
        r = self.unitconv.read_currents()
        str = self.unitconv.compute_strengths(r)        
        return str

    # Sets the value
    def set(self, value:np.array) -> np.array:
        print(f"set strength: {self.elementName}")
        cur = self.unitconv.compute_currents(value)
        self.unitconv.send_currents(cur)
        
    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        pass

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.unitconv.get_strength_units()

#------------------------------------------------------------------------------

class RWStrengthArrayFamily(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a strength (array) of a family
    """

    def __init__(self, elements):
        # Assume we have an array of (virtual) single function magnets
        self.elements = elements

    # Gets the value
    def get(self) -> np.array:
        str = []
        for e in self.elements:
            str.append(e.strength.get()[0])
        return np.array(str)

    # Sets the value
    def set(self, value:np.array) -> np.array:
        for idx,e in enumerate(self.elements):
            e.strength.set(np.array(value[idx]))
        
    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        pass

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.unitconv.get_strength_units()

#------------------------------------------------------------------------------


class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a strength (scalar value) of a simulator or to a control system
    """

    def __init__(self, elementName:str,unitconv:UnitConv):
        self.unitconv = unitconv
        self.elementName = elementName

        #Get element
        #elem = [e for e in lattice if e.Device == elementName]
        #if not elem:
        #    raise ValueError(f"{elementName} not found")
        #if len(elem) != 1:
        #    raise ValueError(f"{elementName} is not unique")
        #if not hasattr(elem[0],attrName):
        #    raise ValueError(f"{elementName} has no field {attrName}")
        #self._element = elem
        #self._attr = attrName

    # Gets the value
    def get(self) -> float:
        #return getattr(self._element,self._attr)
        currents = self.unitconv.read_currents()
        return self.unitconv.compute_strengths(currents)[0]

    # Sets the value
    def set(self, value:float):
        print(f"set strength: {self.elementName}")
        current = self.unitconv.compute_currents([value])
        self.unitconv.send_currents(current)
        #setattr(self._element,self._attr,value)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.unitconv.get_strength_units()[0]


