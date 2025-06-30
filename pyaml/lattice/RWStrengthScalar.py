from pyaml.control import Abstract
from pyaml.magnet.UnitConv import UnitConv
import at
from numpy import double,array

class RWStrengthScalar(Abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a strength (scalar value) of a simulator or to a control system
    """

    def __init__(self, elementName:str,unitconv:UnitConv):
        self.unitconv = unitconv

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
    def get(self) -> double:
        #return getattr(self._element,self._attr)
        currents = self.unitconv.read_currents()
        return self.unitconv.compute_strengths(currents)[0]

    # Sets the value
    def set(self, value:double):
        current = self.unitconv.compute_currents([value])
        self.unitconv.send_currents(current)
        #setattr(self._element,self._attr,value)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:double):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.unitconv.get_strengths_units()[0]


