from pyaml.control import Abstract
from pyaml.magnet.UnitConv import UnitConv
import numpy as np

class RWArray(Abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a scalar array variable of a simulator or to a control system
    """

    def __init__(self, elementName:str,unitconv:UnitConv,nbMultipole:int):
        self.unitconv = unitconv
        #self.cache = self.get() TOTO implement cache initialisation
        self.cache=np.zeros(nbMultipole)

    # Gets the value
    def get(self) -> np.array:
        return self.cache

    # Sets the value
    def set(self, value:np.array) -> np.array:
        print("RWFloatArray: set" + str(value))
        pass
        
    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        pass



