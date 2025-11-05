from ..common import abstract
from ..control.deviceaccesslist import DeviceAccessList
from ..control.deviceaccess import DeviceAccess
from ..magnet.model import MagnetModel
from ..magnet.magnet import Magnet
from ..bpm.bpm_model import BPMModel
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter
from ..common.abstract_aggregator import ScalarAggregator
from numpy import double
import numpy as np
from numpy.typing import NDArray

#------------------------------------------------------------------------------

class CSScalarAggregator(ScalarAggregator):
    """
    Basic control system aggregator for a list of scalar values
    """

    def __init__(self, devs:DeviceAccessList):
        self._devs = devs

    def add_devices(self, devices:DeviceAccess | list[DeviceAccess] ):
        self._devs.add_devices(devices)

    def set(self, value: NDArray[np.float64]):
        self._devs.set(value)

    def set_and_wait(self, value: NDArray[np.float64]):
        self._devs.set_and_wait(value)

    def get(self) -> NDArray[np.float64]:
        return self._devs.get()

    def readback(self) -> np.array:
        return self._devs.readback()

    def unit(self) -> str:
        return self._devs.unit()
    
    def nb_device(self) -> int:
        return self._devs.__len__()

#------------------------------------------------------------------------------

class CSStrengthScalarAggregator(CSScalarAggregator):
    """
    Control system aggregator for a list of magnet strengths.
    This aggregator is in charge of computing hardware setpoints and applying them without overlap.
    When virtual magnets exported from combined function mangets are present (RWMapper), 
    the aggregator prevents to apply several times the same power supply setpoint.
    """

    def __init__(self, peer:CSScalarAggregator):
        CSScalarAggregator.__init__(self,peer._devs)
        self.__models: list[MagnetModel] = []                   # List of magnet model
        self.__modelToMagnet: list[list[tuple[int,int]]] = []   # strengths indexing
        self.__nbMagnet = 0                                     # Number of magnet strengths

    def add_magnet(self, magnet:Magnet):
        # Incoming magnet can be a magnet exported from a CombinedFunctionMagnet or simple magnet.
        # All magnets exported from a same CombinedFunctionMagnet share the same model
        # TODO: check that strength is supported (m.strength may be None)
        strengthIndex = magnet.strength.index() if isinstance(magnet.strength,abstract.RWMapper) else 0
        if magnet.model not in self.__models:
            index = len(self.__models)
            self.__models.append(magnet.model)
            self.__modelToMagnet.append([(self.__nbMagnet,strengthIndex)])
            self._devs.add_devices(magnet.model.get_devices())
        else:
            index = self.__models.index(magnet.model)
            self.__modelToMagnet[index].append((self.__nbMagnet,strengthIndex))
        self.__nbMagnet += 1

    def set(self, value: NDArray[np.float64]):
        allHardwareValues = self._devs.get() # Read all hardware setpoints
        newHardwareValues = np.zeros(self.nb_device())
        hardwareIndex = 0
        for modelIndex,model in enumerate(self.__models):
            nbDev = len(model.get_devices())
            mStrengths = model.compute_strengths( allHardwareValues[hardwareIndex:hardwareIndex+nbDev] )
            for (valueIdx,strengthIdx) in self.__modelToMagnet[modelIndex]:
                mStrengths[strengthIdx] = value[valueIdx]
            newHardwareValues[hardwareIndex:hardwareIndex+nbDev] = model.compute_hardware_values(mStrengths)
            hardwareIndex += nbDev
        self._devs.set(newHardwareValues)

    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")

    def get(self) -> NDArray[np.float64]:
        allHardwareValues = self._devs.get() # Read all hardware setpoints
        allStrength = np.zeros(self.__nbMagnet)
        hardwareIndex = 0
        for modelIndex,model in enumerate(self.__models):
            nbDev = len(model.get_devices())
            mStrengths = model.compute_strengths( allHardwareValues[hardwareIndex:hardwareIndex+nbDev] )
            for (valueIdx,strengthIdx) in self.__modelToMagnet[modelIndex]:
                allStrength[valueIdx] = mStrengths[strengthIdx]
            hardwareIndex += nbDev
        return allStrength

    def readback(self) -> np.array:
        allHardwareValues = self._devs.readback() # Read all hardware readback
        allStrength = np.zeros(self.__nbMagnet)
        hardwareIndex = 0
        for modelIndex,model in enumerate(self.__models):
            nbDev = len(model.get_devices())
            mStrengths = model.compute_strengths( allHardwareValues[hardwareIndex:hardwareIndex+nbDev] )
            for (valueIdx,strengthIdx) in self.__modelToMagnet[modelIndex]:
                allStrength[valueIdx] = mStrengths[strengthIdx]
            hardwareIndex += nbDev
        return allStrength

    def unit(self) -> str:
        return self._devs.unit()


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
        return self.__model.read_position()

    # Gets the unit of the value Assume that x and y has the same unit
    def unit(self) -> str:
        return self.__model.get_pos_devices()[0].unit()

#------------------------------------------------------------------------------

class RWBpmTiltScalar(abstract.ReadFloatScalar):
    """
    Class providing read access to a BPM tilt of a control system
    """
    def __init__(self, model:BPMModel):
        self.__model = model

    # Gets the value
    def get(self) -> float:
        return self.__model.read_tilt()

    def set(self, value:float):
        self.__model.set_tilt(value)

    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")
    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_tilt_device().unit()

#------------------------------------------------------------------------------

class RWBpmOffsetArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a BPM offset of a control system
    """
    def __init__(self, model: BPMModel):
        self.__model = model

    # Gets the value
    def get(self) -> NDArray[np.float64]:
        return self.__model.read_offset()

    # Sets the value
    def set(self, value: NDArray[np.float64]):
        self.__model.set_offset(value) 
    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")
    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_offset_devices()[0].unit()

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

#------------------------------------------------------------------------------

class RBetatronTuneArray(abstract.ReadFloatArray):
    """
    Class providing read write access to betatron tune of a control system.
    """

    def __init__(self, tune_monitor):
        self.__tune_monitor = tune_monitor

    def get(self) -> NDArray:
        # Return horizontal and vertical betatron tunes as a NumPy array
        return np.array([self.__tune_monitor._cfg.tune_h.get(), 
               self.__tune_monitor._cfg.tune_v.get()])

    def unit(self) -> str:
        return self.__tune_monitor._cfg.tune_v.unit()

