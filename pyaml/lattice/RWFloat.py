from pyaml.control import Abstract
from pyaml.magnet.UnitConv import UnitConv
import at
from numpy import double,array

class RWFloat(Abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a scalar double variable of a simulator or to control system
    """

    #def __init__(self,elementName:str,attrName:str,lattice:at.lattice, unitconv:UnitConv):
    def __init__(self, unitconv:UnitConv):
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
        return 0
        #return getattr(self._element,self._attr)

    # Sets the value
    def set(self, value:double):
        current = self.unitconv.get_currents(array([value]))[0]
        print("set(" + str(value) + ")=> current=" + str(current))
        #setattr(self._element,self._attr,value)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:double):
        raise NotImplementedError("Not implemented yet.")




