import numpy as np
import at
from scipy.constants import speed_of_light

from ..control import abstract
from ..magnet.model import MagnetModel
from .polynom_info import PolynomInfo
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter

# TODO handle serialized magnets

#------------------------------------------------------------------------------

class RWHardwareScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a magnet of a simulator in hardware unit.
    Hardware unit is converted from strength using the magnet model
    """

    def __init__(self, elements:list[at.Element], poly:PolynomInfo, model:MagnetModel):
        self.model = model
        self.elements = elements
        self.poly = elements[0].__getattribute__(poly.attName)
        self.polyIdx = poly.index

    def get(self) -> float:
        s = self.poly[self.polyIdx] * self.elements[0].Length
        return self.model.compute_hardware_values([s])[0]
    
    def set(self,value:float):
        s = self.model.compute_strengths([value])[0]
        self.poly[self.polyIdx] = s / self.elements[0].Length

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return self.model.get_hardware_units()[0]
    
#------------------------------------------------------------------------------

class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a strength of a simulator
    """

    def __init__(self, elements:list[at.Element], poly:PolynomInfo, model:MagnetModel):
        self.unitconv = model
        self.elements = elements
        self.poly = elements[0].__getattribute__(poly.attName)
        self.polyIdx = poly.index

    # Gets the value
    def get(self) -> float:
        return self.poly[self.polyIdx] * self.elements[0].Length

    # Sets the value
    def set(self, value:float):
        self.poly[self.polyIdx] = value / self.elements[0].Length

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.unitconv.get_strength_units()[0]

#------------------------------------------------------------------------------

class RWHardwareArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a magnet of a simulator in hardware units.
    Hardware units are converted from strengths using the magnet model
    """

    def __init__(self, elements:list[at.Element], poly:list[PolynomInfo], model:MagnetModel):
        self.elements = elements
        self.poly = []
        self.polyIdx = []
        self.model = model
        for p in poly:
            self.poly.append(elements[0].__getattribute__(p.attName))
            self.polyIdx.append(p.index)

    # Gets the value
    def get(self) -> np.array:  
        nbStrength = len(self.poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            s[i] = self.poly[i][self.polyIdx[i]] * self.elements[0].Length
        return self.model.compute_hardware_values(s)

    # Sets the value
    def set(self, value:np.array):
        nbStrength = len(self.poly)
        s = self.model.compute_strengths(value)
        for i in range(nbStrength):
            self.poly[i][self.polyIdx[i]] = s[i] / self.elements[0].Length

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.model.get_hardware_units()

#------------------------------------------------------------------------------

class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a strength (array) of a simulator
    """

    def __init__(self, elements:list[at.Element], poly:list[PolynomInfo], model:MagnetModel):
        self.elements = elements
        self.poly = []
        self.polyIdx = []
        self.unitconv = model
        for p in poly:
            self.poly.append(elements[0].__getattribute__(p.attName))
            self.polyIdx.append(p.index)

    # Gets the value
    def get(self) -> np.array:  
        nbStrength = len(self.poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            s[i] = self.poly[i][self.polyIdx[i]] * self.elements[0].Length
        return s

    # Sets the value
    def set(self, value:np.array):
        nbStrength = len(self.poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            self.poly[i][self.polyIdx[i]] = value[i] / self.elements[0].Length

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.unitconv.get_strength_units()

#------------------------------------------------------------------------------

class RWRFVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a cavity voltage of a simulator for a given RF trasnmitter.
    """

    def __init__(self, elements:list[at.Element], transmitter:RFTransmitter):
        self.elements = elements
        self.__transmitter = transmitter

    def get(self) -> float:
        sum = 0
        for idx,e in enumerate(self.elements):
            sum += e.Voltage
        return sum
    
    def set(self,value:float):
        v = value / len(self.elements)
        for e in self.elements:
            e.Voltage = v

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return self.__transmitter._cfg.voltage.unit()

#------------------------------------------------------------------------------

class RWRFPhaseScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a cavity phase of a simulator for a given RF trasnmitter.
    """

    def __init__(self, elements:list[at.Element], transmitter:RFTransmitter):
        self.__elements = elements
        self.__transmitter = transmitter

    def get(self) -> float:
        # Assume that all cavities of this transmitter have the same Time Lag and Frequency
        wavelength = speed_of_light / self.__elements[0].Frequency        
        return (wavelength /  self.__elements[0].TimeLag) * 2.0 * np.pi
    
    def set(self,value:float):
        wavelength = speed_of_light / self.__elements[0].Frequency
        for e in self.__elements:
            e.TimeLag = wavelength * value / (2.0 * np.pi)

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return self.__transmitter._cfg.phase.unit()
    
#------------------------------------------------------------------------------

class RWRFFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a simulator.
    """

    def __init__(self, elements:list[at.Element], harmonics:list[float], rf:RFPlant ):
        self.__elements = elements
        self.__harm = harmonics
        self.__rf = rf

    def get(self) -> float:
        # Serialized cavity has the same frequency
        return self.__elements[0].Frequency
    
    def set(self,value:float):
        for idx,e in enumerate(self.__elements):
            e.Frequency = value * self.__harm[idx]

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return self.__rf._cfg.masterclock.unit()

