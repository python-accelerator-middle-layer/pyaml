import at
import numpy as np
from numpy.typing import NDArray
from scipy.constants import speed_of_light

from ..common import abstract
from ..common.abstract_aggregator import ScalarAggregator
from ..common.exception import PyAMLException
from ..magnet.model import MagnetModel
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter
from .polynom_info import PolynomInfo

# TODO handle serialized magnets for magnet array

# ------------------------------------------------------------------------------


class RWHardwareScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a magnet of a simulator in hardware unit.
    Hardware unit is converted from strength using the magnet model
    """

    def __init__(self, elements: list[at.Element], poly: PolynomInfo, model: MagnetModel):
        self.__model = model
        self.__elements = elements
        self.__poly = [e.__getattribute__(poly.attName) for e in elements]
        self.__sign = poly.sign
        self.__polyIdx = poly.index
        self.__length: float = 0.0
        for e in elements:
            self.__length += e.Length

    def get_length(self) -> float:
        return self.__length

    def get(self) -> float:
        s = 0
        for idx, e in enumerate(self.__elements):
            s += self.__poly[idx][self.__polyIdx] * self.__sign * e.Length
        return self.__model.compute_hardware_values([s])[0]

    def set(self, value: float):
        s = self.__model.compute_strengths([value])[0]
        for idx, _ in enumerate(self.__elements):
            self.__poly[idx][self.__polyIdx] = s / (self.__length * self.__sign)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__model.get_hardware_units()[0]

    def get_model(self) -> MagnetModel:
        return self.__model


# ------------------------------------------------------------------------------


class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a strength of a simulator
    """

    def __init__(self, elements: list[at.Element], poly: PolynomInfo, model: MagnetModel):
        self.__model = model
        self.__elements = elements
        self.__poly = [e.__getattribute__(poly.attName) for e in elements]
        self.__sign = poly.sign
        self.__polyIdx = poly.index
        self.__length = 0
        for e in elements:
            self.__length += e.Length

    def get_element_length(self) -> float:
        return self.__length

    # Gets the value
    def get(self) -> float:
        s = 0
        for idx, e in enumerate(self.__elements):
            s += self.__poly[idx][self.__polyIdx] * self.__sign * e.Length
        return s

    # Sets the value
    def set(self, value: float):
        for idx, _ in enumerate(self.__elements):
            self.__poly[idx][self.__polyIdx] = value / (self.__length * self.__sign)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_strength_units()[0]

    # ------------------------------------------------------------------------------
    def get_model(self) -> MagnetModel:
        return self.__model


# ------------------------------------------------------------------------------


class RWSerializedHardware(abstract.ReadWriteFloatScalar):
    def __init__(self, elements: list[RWHardwareScalar], element_index: int):
        self.__elements = elements
        self.__element_index = element_index
        self.__total_length = 0
        for e in elements:
            self.__total_length += e.get_length()

    def get_element_length(self) -> float:
        return self.__elements[self.__element_index].get_length()

    def get_total_length(self) -> float:
        return self.__total_length

    # Gets the value
    def get(self) -> float:
        return self.__elements[self.__element_index].get()

    # Sets the value
    def set(self, value: float):
        [element.set(value) for element in self.__elements]

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__elements[self.__element_index].unit()

    def set_magnet_rigidity(self, brho: np.double):
        [element.get_model().set_magnet_rigidity(brho) for element in self.__elements]


class RWSerializedStrength(abstract.ReadWriteFloatScalar):
    def __init__(
        self,
        elements_strength: list[RWStrengthScalar],
        elements_hardware: list[RWHardwareScalar],
        element_index: int,
    ):
        self.__element = elements_strength[element_index]
        self.__elements_strength = elements_strength
        self.__elements_hardware = elements_hardware
        self.__element_index = element_index
        self.__total_length = 0
        for e in self.__elements_hardware:
            self.__total_length += e.get_length()

    def get_element_length(self) -> float:
        return self.__element.get_element_length()

    def get_total_length(self) -> float:
        return self.__total_length

    # Gets the value
    def get(self) -> float:
        return self.__elements_strength[self.__element_index].get()

    # Sets the value
    def set(self, value: float):
        elements_values = [value * e.get_length() / self.get_total_length() for e in self.__elements_hardware]
        self.__element.set(elements_values[self.__element_index])

        # compute the local hardware value
        hardware_value = self.__elements_hardware[self.__element_index].get()

        # compute the total hardware value
        total_hardware = hardware_value * self.get_total_length() / self.get_element_length()

        # dispatch this value
        for index, element in enumerate(self.__elements_hardware):
            if index != self.__element_index:
                element.set(total_hardware * element.get_length() / self.get_total_length())

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__element.unit()

    def set_magnet_rigidity(self, brho: np.double):
        pass


class RWHardwareArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a magnet of a simulator in hardware units.
    Hardware units are converted from strengths using the magnet model
    """

    def __init__(self, elements: list[at.Element], poly: list[PolynomInfo], model: MagnetModel):
        self.__elements = elements
        self.__poly = []
        self.__polyIdx = []
        self.__sign = []
        self.__model = model
        for p in poly:
            self.__poly.append(elements[0].__getattribute__(p.attName))
            self.__polyIdx.append(p.index)
            self.__sign.append(p.sign)

    # Gets the value
    def get(self) -> np.array:
        nbStrength = len(self.__poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            s[i] = self.__poly[i][self.__polyIdx[i]] * self.__sign[i] * self.__elements[0].Length
        return self.__model.compute_hardware_values(s)

    # Sets the value
    def set(self, value: np.array):
        nbStrength = len(self.__poly)
        s = self.__model.compute_strengths(value)
        for i in range(nbStrength):
            self.__poly[i][self.__polyIdx[i]] = s[i] / (self.__elements[0].Length * self.__sign[i])

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_hardware_units()


# ------------------------------------------------------------------------------


class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a strength (array) of a simulator
    """

    def __init__(self, elements: list[at.Element], poly: list[PolynomInfo], model: MagnetModel):
        self.__elements = elements
        self.__poly = []
        self.__polyIdx = []
        self.__sign = []
        self.__model = model
        for p in poly:
            self.__poly.append(elements[0].__getattribute__(p.attName))
            self.__polyIdx.append(p.index)
            self.__sign.append(p.sign)

    # Gets the value
    def get(self) -> np.array:
        nbStrength = len(self.__poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            s[i] = self.__poly[i][self.__polyIdx[i]] * self.__sign[i] * self.__elements[0].Length
        return s

    # Sets the value
    def set(self, value: np.array):
        nbStrength = len(self.__poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            self.__poly[i][self.__polyIdx[i]] = value[i] / (self.__elements[0].Length * self.__sign[i])

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_strength_units()


# ------------------------------------------------------------------------------


class BPMScalarAggregator(ScalarAggregator):
    """
    BPM simulator aggregator
    """

    def __init__(self, ring: at.Lattice):
        self._lattice = ring
        self._refpts = []
        self._matrices = []

    def add_elem(self, elem: at.Element):
        self._refpts.append(self._lattice.index(elem))
        self._matrices.append(elem._transform)

    def set(self, value: NDArray[np.float64]):
        pass

    def set_and_wait(self, value: NDArray[np.float64]):
        pass

    def get(self) -> np.array:
        return self._tranform().flatten()

    def readback(self) -> np.array:
        return self.get()

    def unit(self) -> str:
        return "m"

    def _tranform(self) -> np.array:
        _, orbit = at.find_orbit(self._lattice, refpts=self._refpts)
        ones = np.ones(len(self._refpts))
        pts = orbit[:, [0, 2]]  # Extract x,y
        # Batch matrices multiplication (homogeneous coordinates)
        return np.matmul(self._matrices, np.column_stack([pts, ones])[:, :, None]).squeeze(-1)


# ------------------------------------------------------------------------------


class BPMHScalarAggregator(BPMScalarAggregator):
    """
    Horizontal BPM simulator aggregator
    """

    def get(self) -> np.array:
        return self._tranform()[:, 0]


# ------------------------------------------------------------------------------


class BPMVScalarAggregator(BPMScalarAggregator):
    """
    Vertical BPM simulator aggregator
    """

    def get(self) -> np.array:
        return self._tranform()[:, 1]


# ------------------------------------------------------------------------------


def update_bpm_transform_matrix(element: at.Element):
    # BPM transformation matrix (homogeneous coordinates)
    tx = element.Offset[0]
    ty = element.Offset[1]
    cos_theta = np.cos(element.Tilt)
    sin_theta = np.sin(element.Tilt)
    if not hasattr(element, "_transform"):
        element._transform = np.empty((2, 3))
    element._transform[:, :] = [[cos_theta, -sin_theta, tx], [sin_theta, cos_theta, ty]]


class RBpmArray(abstract.ReadFloatArray):
    """
    Class providing read access to a BPM position (array) of a simulator.
    Position in pyAT is calculated using find_orbit function, which returns the
    orbit at a specified index. The position is then extracted from the orbit
    array as the first two elements (x, y).
    """

    def __init__(self, element: at.Element, lattice: at.Lattice):
        self._element = element
        self._lattice = lattice

    # Gets the value
    def get(self) -> np.array:
        index = self._lattice.index(self._element)
        _, orbit = at.find_orbit(self._lattice, refpts=index)
        pts = orbit[0, [0, 2]]
        return np.dot(self._element._transform, np.hstack([pts, 1]))  # Use homogeneous coordinates

    # Gets the unit of the value
    def unit(self) -> str:
        return "m"


# ------------------------------------------------------------------------------


class RWBpmOffsetArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a BPM offset (array) of a simulator.
    Offset in pyAT is defined in Offset attribute as a 2-element array.
    """

    def __init__(self, element: at.Element):
        self._element = element

    # Gets the value
    def get(self) -> np.array:
        return self._element.Offset

    # Sets the value
    def set(self, value: np.array):
        self._element.Offset = value
        update_bpm_transform_matrix(self._element)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return "m"  # Assuming all offsets are in m


# ------------------------------------------------------------------------------


class RWBpmTiltScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a BPM tilt of a simulator. Tilt in
    pyAT is defined in Rotation attribute as a first element.
    """

    def __init__(self, element: at.Element):
        self._element = element

    # Gets the value
    def get(self) -> float:
        return self._element.Tilt

    # Sets the value
    def set(
        self,
        value: float,
    ):
        self._element.Tilt = value
        update_bpm_transform_matrix(self._element)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return "rad"  # Assuming BPM tilts are in rad


# ------------------------------------------------------------------------------


class RWRFVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a cavity voltage
    of a simulator for a given RF trasnmitter.
    """

    def __init__(self, elements: list[at.Element]):
        self.__elements = elements

    def get(self) -> float:
        sum = 0
        for _idx, e in enumerate(self.__elements):
            sum += e.Voltage
        return sum

    def set(self, value: float):
        v = value / len(self.__elements)
        for e in self.__elements:
            e.Voltage = v

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return "V"


# ------------------------------------------------------------------------------


class RWRFPhaseScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a cavity phase of
    a simulator for a given RF trasnmitter.
    """

    def __init__(self, elements: list[at.Element]):
        self.__elements = elements

    def get(self) -> float:
        # Assume that all cavities of this transmitter
        # have the same Time Lag and Frequency
        wavelength = speed_of_light / self.__elements[0].Frequency
        return (wavelength / self.__elements[0].TimeLag) * 2.0 * np.pi

    def set(self, value: float):
        wavelength = speed_of_light / self.__elements[0].Frequency
        for e in self.__elements:
            e.TimeLag = wavelength * value / (2.0 * np.pi)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return "rad"


# ------------------------------------------------------------------------------


class RWRFFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a simulator.
    """

    def __init__(self, elements: list[at.Element], harmonics: list[float]):
        self.__elements = elements
        self.__harm = harmonics

    def get(self) -> float:
        # Serialized cavity has the same frequency
        return self.__elements[0].Frequency

    def set(self, value: float):
        for idx, e in enumerate(self.__elements):
            e.Frequency = value * self.__harm[idx]

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return "Hz"


# ------------------------------------------------------------------------------


class RWRFATFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a simulator using
    AT methods.
    """

    def __init__(self, ring: at.Lattice):
        self.__ring = ring

    def get(self) -> float:
        return self.__ring.get_rf_frequency()

    def set(self, value: float):
        self.__ring.set_rf_frequency(value)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return "Hz"


# ------------------------------------------------------------------------------


class RWRFATotalVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a RF voltage of a simulator using AT methods.
    """

    def __init__(self, ring: at.Lattice):
        self.__ring = ring

    def get(self) -> float:
        return self.__ring.get_rf_voltage()

    def set(self, value: float):
        self.__ring.set_rf_voltage(value)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return "V"


# ------------------------------------------------------------------------------


class RBetatronTuneArray(abstract.ReadFloatArray):
    """
    Class providing read-only access to the betatron tune of a ring.
    """

    def __init__(self, ring: at.Lattice):
        self.__ring = ring

    def get(self) -> float:
        return self.__ring.get_tune()[:2]

    def unit(self) -> str:
        return "1"


# ------------------------------------------------------------------------------
