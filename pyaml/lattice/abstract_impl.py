from ..common import abstract
from ..common.exception import PyAMLException
from ..magnet.model import MagnetModel
from .polynom_info import PolynomInfo
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter
from ..common.abstract_aggregator import ScalarAggregator

import numpy as np
import at
from scipy.constants import speed_of_light
from numpy.typing import NDArray

# TODO handle serialized magnets

#------------------------------------------------------------------------------

class RWHardwareScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a magnet of a simulator in hardware unit.
    Hardware unit is converted from strength using the magnet model
    """

    def __init__(self, elements:list[at.Element], poly:PolynomInfo, model:MagnetModel):
        self.__model = model
        self.__elements = elements
        self.__poly = elements[0].__getattribute__(poly.attName)
        self.__polyIdx = poly.index

    def get(self) -> float:
        s = self.__poly[self.__polyIdx] * self.__elements[0].Length
        return self.__model.compute_hardware_values([s])[0]
    
    def set(self,value:float):
        s = self.__model.compute_strengths([value])[0]
        self.__poly[self.__polyIdx] = s / self.__elements[0].Length

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return self.__model.get_hardware_units()[0]
    
#------------------------------------------------------------------------------

class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a strength of a simulator
    """

    def __init__(self, elements:list[at.Element], poly:PolynomInfo, model:MagnetModel):
        self.__model = model
        self.__elements = elements
        self.__poly = elements[0].__getattribute__(poly.attName)
        self.__polyIdx = poly.index

    # Gets the value
    def get(self) -> float:
        return self.__poly[self.__polyIdx] * self.__elements[0].Length

    # Sets the value
    def set(self, value:float):
        self.__poly[self.__polyIdx] = value / self.__elements[0].Length

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_strength_units()[0]

#------------------------------------------------------------------------------

class RWHardwareArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a magnet of a simulator in hardware units.
    Hardware units are converted from strengths using the magnet model
    """

    def __init__(self, elements:list[at.Element], poly:list[PolynomInfo], model:MagnetModel):
        self.__elements = elements
        self.__poly = []
        self.__polyIdx = []
        self.__model = model
        for p in poly:
            self.__poly.append(elements[0].__getattribute__(p.attName))
            self.__polyIdx.append(p.index)

    # Gets the value
    def get(self) -> np.array:  
        nbStrength = len(self.__poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            s[i] = self.__poly[i][self.__polyIdx[i]] * self.__elements[0].Length
        return self.__model.compute_hardware_values(s)

    # Sets the value
    def set(self, value:np.array):
        nbStrength = len(self.__poly)
        s = self.__model.compute_strengths(value)
        for i in range(nbStrength):
            self.__poly[i][self.__polyIdx[i]] = s[i] / self.__elements[0].Length

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_hardware_units()

#------------------------------------------------------------------------------

class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a strength (array) of a simulator
    """

    def __init__(self, elements:list[at.Element], poly:list[PolynomInfo], model:MagnetModel):
        self.__elements = elements
        self.__poly = []
        self.__polyIdx = []
        self.__model = model
        for p in poly:
            self.__poly.append(elements[0].__getattribute__(p.attName))
            self.__polyIdx.append(p.index)

    # Gets the value
    def get(self) -> np.array:  
        nbStrength = len(self.__poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            s[i] = self.__poly[i][self.__polyIdx[i]] * self.__elements[0].Length
        return s

    # Sets the value
    def set(self, value:np.array):
        nbStrength = len(self.__poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            self.__poly[i][self.__polyIdx[i]] = value[i] / self.__elements[0].Length

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_strength_units()
    

#------------------------------------------------------------------------------

class BPMScalarAggregator(ScalarAggregator):
    """
    BPM simulator aggregator
    """

    def __init__(self, ring:at.Lattice):
        self.__lattice = ring
        self.__refpts = []

    def add_elem(self,elem:at.Element):
        self.__refpts.append(self.__lattice.index(elem))

    def set(self, value: NDArray[np.float64]):
        pass

    def set_and_wait(self, value: NDArray[np.float64]):
        pass

    def get(self) -> np.array:
        _, orbit = at.find_orbit(self.__lattice, refpts=self.__refpts)
        return orbit[:, [0, 2]].flatten()

    def readback(self) -> np.array:
        return self.get()

    def unit(self) -> str:
        return 'm'
    
#------------------------------------------------------------------------------

class BPMVScalarAggregator(BPMScalarAggregator):
    """
    Vertical BPM simulator aggregator
    """

    def get(self) -> np.array:
        _, orbit = at.find_orbit(self.__lattice, refpts=self.__refpts)
        return orbit[:, 0]

#------------------------------------------------------------------------------

class BPMHScalarAggregator(BPMScalarAggregator):
    """
    Horizontal BPM simulator aggregator
    """

    def get(self) -> np.array:
        _, orbit = at.find_orbit(self.__lattice, refpts=self.__refpts)
        return orbit[:, 2]

#------------------------------------------------------------------------------

class RBpmArray(abstract.ReadFloatArray):
    """
    Class providing read access to a BPM position (array) of a simulator.
    Position in pyAT is calculated using find_orbit function, which returns the
    orbit at a specified index. The position is then extracted from the orbit
    array as the first two elements (x, y).
    """

    def __init__(self, element: at.Element, lattice: at.Lattice):
        self.__element = element
        self.__lattice = lattice
        

    # Gets the value
    def get(self) -> np.array:
        index = self.__lattice.index(self.__element)
        _, orbit = at.find_orbit(self.__lattice, refpts=index)
        return orbit[0, [0, 2]]

    # Gets the unit of the value
    def unit(self) -> str:
        return 'm'

#------------------------------------------------------------------------------

class RWBpmOffsetArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a BPM offset (array) of a simulator. 
    Offset in pyAT is defined in Offset attribute as a 2-element array.
    """

    def __init__(self, element:at.Element):
        self.__element = element
        try:
            self.__offset = element.__getattribute__('Offset')
        except AttributeError:
            self.__offset = None

    # Gets the value
    def get(self) -> np.array:  
        if self.__offset is None:
            raise PyAMLException("Element does not have an Offset attribute.")
        return self.__offset

    # Sets the value
    def set(self, value:np.array):
        if self.__offset is None:
            raise PyAMLException("Element does not have an Offset attribute.")
        if len(value) != 2:
            raise PyAMLException("BPM offset must be a 2-element array.")
        self.__offset = value

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return 'm'  # Assuming all offsets are in m

#------------------------------------------------------------------------------

class RWBpmTiltScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a BPM tilt of a simulator. Tilt in
    pyAT is defined in Rotation attribute as a first element.
    """

    def __init__(self, element:at.Element):
        self.__element = element
        try:
            self.__tilt = element.__getattribute__('Rotation')[0]
        except AttributeError:
            self.__tilt = None

    # Gets the value
    def get(self) -> float:
        if self.__tilt is None:
            raise ValueError("Element does not have a Tilt attribute.")
        return self.__tilt

    # Sets the value
    def set(self, value:float, ):
        self.__tilt = value
        self.__element.__setattr__('Rotation', [value, None, None])

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return 'rad'  # Assuming BPM tilts are in rad

#------------------------------------------------------------------------------

class RWRFVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a cavity voltage of a simulator for a given RF trasnmitter.
    """

    def __init__(self, elements:list[at.Element]):
        self.__elements = elements

    def get(self) -> float:
        sum = 0
        for idx,e in enumerate(self.__elements):
            sum += e.Voltage
        return sum
    
    def set(self,value:float):
        v = value / len(self.__elements)
        for e in self.__elements:
            e.Voltage = v

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return "V"

#------------------------------------------------------------------------------

class RWRFPhaseScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a cavity phase of a simulator for a given RF trasnmitter.
    """

    def __init__(self, elements:list[at.Element]):
        self.__elements = elements

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
        return "rad"
    
#------------------------------------------------------------------------------

class RWRFFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a simulator.
    """

    def __init__(self, elements:list[at.Element], harmonics:list[float]):
        self.__elements = elements
        self.__harm = harmonics

    def get(self) -> float:
        # Serialized cavity has the same frequency
        return self.__elements[0].Frequency
    
    def set(self,value:float):
        for idx,e in enumerate(self.__elements):
            e.Frequency = value * self.__harm[idx]

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return "Hz"

#------------------------------------------------------------------------------

class RWRFATFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a simulator using
    AT methods.
    """

    def __init__(self, ring: at.Lattice):
        self.__ring = ring

    def get(self) -> float:
        return self.__ring.get_rf_frequency()
    
    def set(self,value:float):
        self.__ring.set_rf_frequency(value)

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return 'Hz'
    
#------------------------------------------------------------------------------

class RWRFATotalVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a RF voltage of a simulator using AT methods.
    """

    def __init__(self, ring: at.Lattice):
        self.__ring = ring

    def get(self) -> float:
        return self.__ring.get_rf_voltage()
    
    def set(self,value:float):
        self.__ring.set_rf_voltage(value)

    def set_and_wait(self, value:float):
        raise NotImplementedError("Not implemented yet.")
        
    def unit(self) -> str:
        return 'V'

#------------------------------------------------------------------------------

class RBetatronTuneArray(abstract.ReadFloatArray):
    """
    Class providing read-only access to the betatron tune of a ring.
    """

    def __init__(self, ring: at.Lattice):
        self.__ring = ring
        
    def get(self) -> float:
        return self.__ring.get_tune()[:2]

    def unit(self) -> str:
        return '1'

