from pyaml.control import Abstract
from numpy import double,array

class RWMapper(Abstract.ReadWriteFloatScalar):
    """
    Class mapping a scalar to an element of an array
    """
    def __init__(self, bind, idx:int):
        self.bind = bind
        self.idx = idx

    # Gets the value
    def get(self) -> double:
        return self.bind.get()[self.idx]

    # Sets the value
    def set(self, value:double):
        arr = self.bind.get()
        arr[self.idx] = value
        self.bind.set(arr)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:double):
        raise NotImplementedError("Not implemented yet.")






