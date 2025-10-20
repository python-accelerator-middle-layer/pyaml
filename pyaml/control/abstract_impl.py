from pyaml.control import abstract
from pyaml.magnet.model import MagnetModel
from pyaml.bpm.bpm_model import BPMModel
import numpy as np
from numpy.typing import NDArray
#------------------------------------------------------------------------------

class RWHardwareScalar(abstract.ReadFloatScalar):
    """
    Class providing read write access to a magnet of a control system (in hardware units)
    """
    def __init__(self, model:MagnetModel):
        self.model = model

    def get(self) -> float:
        return self.model.read_hardware_values()[0]
    
    def set(self, value:float):
        self.model.send_harware_values([value])
        
    def unit(self) -> str:
        return self.model.get_hardware_units()[0]

    def index(self) -> int:
        return 0

#------------------------------------------------------------------------------

class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a strength of a control system
    """

    def __init__(self, model:MagnetModel):
        self.__model = model

    # Gets the value
    def get(self) -> float:
        currents = self.__model.read_hardware_values()
        return self.__model.compute_strengths(currents)[0]

    # Sets the value
    def set(self, value:float):
        current = self.__model.compute_hardware_values([value])
        self.__model.send_harware_values(current)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_strength_units()[0]

    def index(self) -> int:
        return 0

#------------------------------------------------------------------------------

class RWHardwareArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a magnet array of a control system (in hardware units)
    """
    def __init__(self, model:MagnetModel):
        self.model = model

    # Gets the value
    def get(self) -> np.array:
        return self.model.read_hardware_values()

    # Sets the value
    def set(self, value:np.array):
        self.model.send_harware_values(value)
        
    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")


    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.model.get_hardware_units()

#------------------------------------------------------------------------------

class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to magnet strengths of a control system
    """
    def __init__(self, model:MagnetModel):
        self.model = model

    # Gets the value
    def get(self) -> np.array:
        r = self.model.read_hardware_values()
        str = self.model.compute_strengths(r)        
        return str

    # Sets the value
    def set(self, value:np.array):
        cur = self.model.compute_hardware_values(value)
        self.model.send_harware_values(cur)
        
    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.model.get_strength_units()

#------------------------------------------------------------------------------

class RBpmArray(abstract.ReadFloatArray):
    """
    Class providing read access to a BPM array of a control system
    """
    def __init__(self, model:BPMModel):
        self.__model = model

    # Gets the value
    def get(self) -> np.array:
        return self.__model.read_hardware_positions()

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_hardware_position_units()

#------------------------------------------------------------------------------

class RWBpmTiltScalar(abstract.ReadFloatScalar):
    """
    Class providing read access to a BPM tilt of a control system
    """
    def __init__(self, model:BPMModel):
        self.__model = model

    # Gets the value
    def get(self) -> float:
        return self.__model.read_hardware_tilt_value()

    def set(self, value:float):
        self.__model.set_hardware_tilt_value(value)

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_hardware_angle_unit()

#------------------------------------------------------------------------------

class RWBpmOffsetArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a BPM offset of a control system
    """
    def __init__(self, model: BPMModel):
        self.__model = model

    # Gets the value
    def get(self) -> NDArray[np.float64]:
        return self.__model.read_hardware_offset_values()

    # Sets the value
    def set(self, value: NDArray[np.float64]):
        self.__model.set_hardware_offset_values(value)

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_hardware_position_units()[0]


