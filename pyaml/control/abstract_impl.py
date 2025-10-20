from numpy import double
import numpy as np

from ..control import abstract
from ..magnet.model import MagnetModel
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter

#------------------------------------------------------------------------------

class RWHardwareScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a magnet of a control system (in hardware units)
    """

    def __init__(self, model:MagnetModel):
        self.__model = model

    def get(self) -> float:
        return self.__model.read_hardware_values()[0]
    
    def set(self, value:float):
        self.__model.send_hardware_values(np.array([value]))

    def set_and_wait(self, value: double):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__model.get_hardware_units()[0]

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
        self.__model.send_hardware_values(current)

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
        self.__model = model

    # Gets the value
    def get(self) -> np.array:
        return self.__model.read_hardware_values()

    # Sets the value
    def set(self, value:np.array):
        self.__model.send_hardware_values(value)
        
    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")


    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_hardware_units()

#------------------------------------------------------------------------------

class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to magnet strengths of a control system
    """
    def __init__(self, model:MagnetModel):
        self.__model = model

    # Gets the value
    def get(self) -> np.array:
        r = self.__model.read_hardware_values()
        str = self.__model.compute_strengths(r)
        return str

    # Sets the value
    def set(self, value:np.array):
        cur = self.__model.compute_hardware_values(value)
        self.__model.send_hardware_values(cur)

    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_strength_units()


#------------------------------------------------------------------------------

class RWRFVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity voltage of a control system.
    """

    def __init__(self, transmitter:RFTransmitter):
        self.__transmitter = transmitter

    def get(self) -> float:        
        return self.__transmitter._cfg.voltage.get()
    
    def set(self,value:float):
        return self.__transmitter._cfg.voltage.set(value)

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return self.__transmitter._cfg.voltage.unit()
    
#------------------------------------------------------------------------------

class RWRFFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a RF frequency of a control system.
    """

    def __init__(self, rf:RFPlant ):
        self.__rf = rf

    def get(self) -> float:
        # Serialized cavity has the same frequency
        return self.__rf._cfg.masterclock.get()

    def set(self,value:float):
        return self.__rf._cfg.masterclock.set(value)

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__rf._cfg.masterclock.unit()

