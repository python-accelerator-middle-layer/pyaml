from numpy import double
from pyaml.control import abstract
from pyaml.magnet.model import MagnetModel
from pyaml.bpm.bpm_model import BPMModel
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter
import numpy as np
from numpy.typing import NDArray
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

    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")
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
    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")
    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_hardware_position_units()[0]

#------------------------------------------------------------------------------

class RWRFVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity voltage for a transmitter of a control system.
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

class RWRFPhaseScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity phase for a transmitter of a control system.
    """

    def __init__(self, transmitter:RFTransmitter):
        self.__transmitter = transmitter

    def get(self) -> float:        
        return self.__transmitter._cfg.phase.get()
    
    def set(self,value:float):
        return self.__transmitter._cfg.phase.set(value)

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return self.__transmitter._cfg.phase.unit()
    
#------------------------------------------------------------------------------

class RWRFFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a control system.
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

