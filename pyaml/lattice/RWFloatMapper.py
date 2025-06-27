from pyaml.control import Abstract
from numpy import double,array

class RWFloatMapper(Abstract.ReadWriteFloatScalar):
    """
    Class mapping a srength to multipole (used for CombinedFunctionMagnet)
    """
    def __init__(self, bind:Abstract.ReadWriteFloatArray, idx:int):
        self.bind = bind
        self.idx = idx

    # Gets the value
    def get(self) -> double:
        return self.bind.get()[self.idx]

    # Sets the value
    def set(self, value:double):
        arr = self.bind.get()
        arr[self.idx] = value
        return self.bind.set(arr)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:double):
        raise NotImplementedError("Not implemented yet.")






