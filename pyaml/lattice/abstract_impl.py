"""Read/write interfaces for simulated lattice elements.

This module adapts Accelerator Toolbox lattice elements to PyAML accessors for
magnet strengths, hardware values, BPM readings, RF parameters, and tune data.
"""

import at
import numpy as np
from numpy.typing import NDArray
from scipy.constants import speed_of_light

from ..common import abstract
from ..common.abstract_aggregator import ScalarAggregator
from ..magnet.model import MagnetModel
from .polynom_info import PolynomInfo

# TODO handle serialized magnets for magnet array

# ------------------------------------------------------------------------------


class RWHardwareScalar(abstract.ReadWriteFloatScalar):
    """
    Provide read/write access to a simulated magnet in hardware units.

    Hardware values are converted through the associated magnet model while
    the underlying lattice polynomial is updated on writes.
    """

    def __init__(self, elements: list[at.Element], poly: PolynomInfo, model: MagnetModel):
        """
        Initialize the RWHardwareScalar.

        Parameters
        ----------
        elements : list[at.Element]
            Input value for this operation.
        poly : PolynomInfo
            Input value for this operation.
        model : MagnetModel
            Input value for this operation.
        """
        self._model = model
        self._elements = elements
        self._poly = [e.__getattribute__(poly.attName) for e in elements]
        self._sign = poly.sign
        self._polyIdx = poly.index
        self._length: float = 0.0
        for e in elements:
            self._length += e.Length

    def get_length(self) -> float:
        """Return the total length of the lattice elements."""
        return self._length

    def get(self) -> float:
        """Return the current value."""
        s = 0
        for idx, e in enumerate(self._elements):
            s += self._poly[idx][self._polyIdx] * self._sign * e.Length
        return self._model.compute_hardware_values([s])[0]

    def set(self, value: float):
        """
        Set the current value.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        s = self._model.compute_strengths([value])[0]
        for idx, _ in enumerate(self._elements):
            self._poly[idx][self._polyIdx] = s / (self._length * self._sign)

    def set_and_wait(self, value: float):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the value unit."""
        return self._model.get_hardware_units()[0]

    def get_model(self) -> MagnetModel:
        """Return the associated magnet model."""
        return self._model


# ------------------------------------------------------------------------------


class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Provide read/write access to a simulated magnet strength.

    The accessor aggregates the selected lattice polynomial over all mapped
    elements and distributes writes across those elements.
    """

    def __init__(self, elements: list[at.Element], poly: PolynomInfo, model: MagnetModel):
        """
        Initialize the RWStrengthScalar.

        Parameters
        ----------
        elements : list[at.Element]
            Input value for this operation.
        poly : PolynomInfo
            Input value for this operation.
        model : MagnetModel
            Input value for this operation.
        """
        self._model = model
        self._elements = elements
        self._poly = [e.__getattribute__(poly.attName) for e in elements]
        self._sign = poly.sign
        self._polyIdx = poly.index
        self._length = 0
        for e in elements:
            self._length += e.Length

    def get_element_length(self) -> float:
        """Return the total length of the represented element."""
        return self._length

    # Gets the value
    def get(self, polynom: str = None, polyidx: int = None) -> float:
        """
        Return the current value.

        Parameters
        ----------
        polynom : str
            Input value for this operation.
        polyidx : int
            Input value for this operation.

        Returns
        -------
        float
            Result produced by the operation.
        """
        if polynom is None:
            pIdx = self._polyIdx
            poly = self._poly
        else:
            # Override strength access
            pIdx = polyidx
            poly = [e.__getattribute__(polynom) for e in self._elements]

        s = 0
        for idx, e in enumerate(self._elements):
            s += poly[idx][pIdx] * self._sign * e.Length
        return s

    # Sets the value
    def set(self, value: float, polynom: str = None, polyidx: int = None):
        """
        Set the current value.

        Parameters
        ----------
        value : float
            Input value for this operation.
        polynom : str
            Input value for this operation.
        polyidx : int
            Input value for this operation.
        """
        if polynom is None:
            pIdx = self._polyIdx
            poly = self._poly
        else:
            # Override strength access
            pIdx = polyidx
            poly = [e.__getattribute__(polynom) for e in self._elements]

        for idx, _ in enumerate(self._elements):
            poly[idx][pIdx] = value / (self._length * self._sign)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        """Return the value unit."""
        return self._model.get_strength_units()[0]

    # ------------------------------------------------------------------------------
    def get_model(self) -> MagnetModel:
        """Return the associated magnet model."""
        return self._model


# ------------------------------------------------------------------------------


class RWSerializedHardware(abstract.ReadWriteFloatScalar):
    """
    RWSerializedHardware configuration or runtime object.

    Parameters
    ----------
    elements : list[RWHardwareScalar]
        Input value for this operation.
    element_index : int
        Input value for this operation.
    """

    def __init__(self, elements: list[RWHardwareScalar], element_index: int):
        """
        Initialize the RWSerializedHardware.

        Parameters
        ----------
        elements : list[RWHardwareScalar]
            Input value for this operation.
        element_index : int
            Input value for this operation.
        """
        self.__elements = elements
        self.__element_index = element_index
        self.__total_length = 0
        for e in elements:
            self.__total_length += e.get_length()

    def get_element_length(self) -> float:
        """Return the total length of the represented element."""
        return self.__elements[self.__element_index].get_length()

    def get_total_length(self) -> float:
        """Return the total length of the represented elements."""
        return self.__total_length

    # Gets the value
    def get(self) -> float:
        """Return the current value."""
        return self.__elements[self.__element_index].get()

    # Sets the value
    def set(self, value: float):
        """
        Set the current value.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        [element.set(value) for element in self.__elements]

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        """Return the value unit."""
        return self.__elements[self.__element_index].unit()

    def set_magnet_rigidity(self, brho: np.double):
        """
        Set the magnetic rigidity used for conversion.

        Parameters
        ----------
        brho : np.double
            Input value for this operation.
        """
        [element.get_model().set_magnet_rigidity(brho) for element in self.__elements]


class RWSerializedStrength(abstract.ReadWriteFloatScalar):
    """
    RWSerializedStrength configuration or runtime object.

    Parameters
    ----------
    elements_strength : list[RWStrengthScalar]
        Input value for this operation.
    elements_hardware : list[RWHardwareScalar]
        Input value for this operation.
    element_index : int
        Input value for this operation.
    """

    def __init__(
        self,
        elements_strength: list[RWStrengthScalar],
        elements_hardware: list[RWHardwareScalar],
        element_index: int,
    ):
        """
        Initialize the RWSerializedStrength.

        Parameters
        ----------
        elements_strength : list[RWStrengthScalar]
            Input value for this operation.
        elements_hardware : list[RWHardwareScalar]
            Input value for this operation.
        element_index : int
            Input value for this operation.
        """
        self.__element = elements_strength[element_index]
        self.__elements_strength = elements_strength
        self.__elements_hardware = elements_hardware
        self.__element_index = element_index
        self.__total_length = 0
        for e in self.__elements_hardware:
            self.__total_length += e.get_length()

    def get_element_length(self) -> float:
        """Return the total length of the represented element."""
        return self.__element.get_element_length()

    def get_total_length(self) -> float:
        """Return the total length of the represented elements."""
        return self.__total_length

    # Gets the value
    def get(self) -> float:
        """Return the current value."""
        return self.__elements_strength[self.__element_index].get()

    # Sets the value
    def set(self, value: float):
        """
        Set the current value.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
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
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        """Return the value unit."""
        return self.__element.unit()

    def set_magnet_rigidity(self, brho: np.double):
        """
        Set the magnetic rigidity used for conversion.

        Parameters
        ----------
        brho : np.double
            Input value for this operation.
        """
        pass


class RWHardwareArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a magnet of a simulator in hardware units.
    Hardware units are converted from strengths using the magnet model
    """

    def __init__(self, elements: list[at.Element], poly: list[PolynomInfo], model: MagnetModel):
        """
        Initialize the RWHardwareArray.

        Parameters
        ----------
        elements : list[at.Element]
            Input value for this operation.
        poly : list[PolynomInfo]
            Input value for this operation.
        model : MagnetModel
            Input value for this operation.
        """
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
        """Return the current value."""
        nbStrength = len(self.__poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            s[i] = self.__poly[i][self.__polyIdx[i]] * self.__sign[i] * self.__elements[0].Length
        return self.__model.compute_hardware_values(s)

    # Sets the value
    def set(self, value: np.array):
        """
        Set the current value.

        Parameters
        ----------
        value : np.array
            Input value for this operation.
        """
        nbStrength = len(self.__poly)
        s = self.__model.compute_strengths(value)
        for i in range(nbStrength):
            self.__poly[i][self.__polyIdx[i]] = s[i] / (self.__elements[0].Length * self.__sign[i])

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : np.array
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        """Return the value unit."""
        return self.__model.get_hardware_units()


# ------------------------------------------------------------------------------


class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a strength (array) of a simulator
    """

    def __init__(self, elements: list[at.Element], poly: list[PolynomInfo], model: MagnetModel):
        """
        Initialize the RWStrengthArray.

        Parameters
        ----------
        elements : list[at.Element]
            Input value for this operation.
        poly : list[PolynomInfo]
            Input value for this operation.
        model : MagnetModel
            Input value for this operation.
        """
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
        """Return the current value."""
        nbStrength = len(self.__poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            s[i] = self.__poly[i][self.__polyIdx[i]] * self.__sign[i] * self.__elements[0].Length
        return s

    # Sets the value
    def set(self, value: np.array):
        """
        Set the current value.

        Parameters
        ----------
        value : np.array
            Input value for this operation.
        """
        nbStrength = len(self.__poly)
        s = np.zeros(nbStrength)
        for i in range(nbStrength):
            self.__poly[i][self.__polyIdx[i]] = value[i] / (self.__elements[0].Length * self.__sign[i])

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : np.array
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        """Return the value unit."""
        return self.__model.get_strength_units()


# ------------------------------------------------------------------------------


class BPMScalarAggregator(ScalarAggregator):
    """
    BPM simulator aggregator
    """

    def __init__(self, ring: at.Lattice):
        """
        Initialize the BPMScalarAggregator.

        Parameters
        ----------
        ring : at.Lattice
            Input value for this operation.
        """
        self._lattice = ring
        self._refpts = []
        self._matrices = []

    def add_elem(self, elem: at.Element):
        """
        Add a lattice element to the aggregate.

        Parameters
        ----------
        elem : at.Element
            Input value for this operation.
        """
        self._refpts.append(self._lattice.index(elem))
        self._matrices.append(elem._transform)

    def set(self, value: NDArray[np.float64]):
        """
        Set the current value.

        Parameters
        ----------
        value : NDArray[np.float64]
            Input value for this operation.
        """
        pass

    def set_and_wait(self, value: NDArray[np.float64]):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : NDArray[np.float64]
            Input value for this operation.
        """
        pass

    def get(self) -> np.array:
        """Return the current value."""
        return self._transform().flatten()

    def readback(self) -> np.array:
        """Return the current readback value."""
        return self.get()

    def unit(self) -> str:
        """Return the value unit."""
        return "m"

    def _transform(self) -> np.array:
        """Transform the configured value for the lattice interface."""
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
        """Return the current value."""
        return self._transform()[:, 0]


# ------------------------------------------------------------------------------


class BPMVScalarAggregator(BPMScalarAggregator):
    """
    Vertical BPM simulator aggregator
    """

    def get(self) -> np.array:
        """Return the current value."""
        return self._transform()[:, 1]


# ------------------------------------------------------------------------------


def update_bpm_transform_matrix(element: at.Element):
    # BPM transformation matrix (homogeneous coordinates)
    """
    Update the coordinate transform for a beam-position monitor.

    The transform combines the BPM element's horizontal and vertical offsets
    with its tilt, allowing measured positions to be expressed in the BPM
    coordinate system.

    Parameters
    ----------
    element : at.Element
        BPM lattice element with ``Offset`` and ``Tilt`` attributes. The
        resulting matrix is stored on the element as ``_transform``.
    """
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
        """
        Initialize the RBpmArray.

        Parameters
        ----------
        element : at.Element
            Input value for this operation.
        lattice : at.Lattice
            Input value for this operation.
        """
        self._element = element
        self._lattice = lattice

    # Gets the value
    def get(self) -> np.array:
        """Return the current value."""
        index = self._lattice.index(self._element)
        _, orbit = at.find_orbit(self._lattice, refpts=index)
        pts = orbit[0, [0, 2]]
        return np.dot(self._element._transform, np.hstack([pts, 1]))  # Use homogeneous coordinates

    # Gets the unit of the value
    def unit(self) -> str:
        """Return the value unit."""
        return "m"


# ------------------------------------------------------------------------------


class RWBpmOffsetArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a BPM offset (array) of a simulator.
    Offset in pyAT is defined in Offset attribute as a 2-element array.
    """

    def __init__(self, element: at.Element):
        """
        Initialize the RWBpmOffsetArray.

        Parameters
        ----------
        element : at.Element
            Input value for this operation.
        """
        self._element = element

    # Gets the value
    def get(self) -> np.array:
        """Return the current value."""
        return self._element.Offset

    # Sets the value
    def set(self, value: np.array):
        """
        Set the current value.

        Parameters
        ----------
        value : np.array
            Input value for this operation.
        """
        self._element.Offset = value
        update_bpm_transform_matrix(self._element)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : np.array
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        """Return the value unit."""
        return "m"  # Assuming all offsets are in m


# ------------------------------------------------------------------------------


class RWBpmTiltScalar(abstract.ReadWriteFloatScalar):
    """
    Provide read/write access to a simulated BPM tilt.

    The value is read from and written to the Accelerator Toolbox ``Tilt``
    attribute. Writing the tilt also refreshes the BPM coordinate transform.
    """

    def __init__(self, element: at.Element):
        """
        Initialize a BPM-tilt accessor.

        Parameters
        ----------
        element : at.Element
            BPM lattice element whose ``Tilt`` attribute is accessed.
        """
        self._element = element

    # Gets the value
    def get(self) -> float:
        """Return the current value."""
        return self._element.Tilt

    # Sets the value
    def set(
        self,
        value: float,
    ):
        """
        Set the current value.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        self._element.Tilt = value
        update_bpm_transform_matrix(self._element)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        """Return the value unit."""
        return "rad"  # Assuming BPM tilts are in rad


# ------------------------------------------------------------------------------


class RWRFVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a cavity voltage
    of a simulator for a given RF trasnmitter.
    """

    def __init__(self, elements: list[at.Element]):
        """
        Initialize the RWRFVoltageScalar.

        Parameters
        ----------
        elements : list[at.Element]
            Input value for this operation.
        """
        self.__elements = elements

    def get(self) -> float:
        """Return the current value."""
        sum = 0
        for _idx, e in enumerate(self.__elements):
            sum += e.Voltage
        return sum

    def set(self, value: float):
        """
        Set the current value.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        v = value / len(self.__elements)
        for e in self.__elements:
            e.Voltage = v

    def set_and_wait(self, value: float):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the value unit."""
        return "V"


# ------------------------------------------------------------------------------


class RWRFPhaseScalar(abstract.ReadWriteFloatScalar):
    """
    Provide read/write access to the phase of simulated RF cavities.

    Accelerator Toolbox represents the phase through each cavity's
    ``TimeLag`` attribute. This accessor uses the first cavity's frequency and
    keeps the phase synchronized across all cavities in the transmitter.
    """

    def __init__(self, elements: list[at.Element]):
        """
        Initialize an RF-cavity phase accessor.

        Parameters
        ----------
        elements : list[at.Element]
            RF cavity elements sharing the transmitter phase.
        """
        self.__elements = elements

    def get(self) -> float:
        # Assume that all cavities of this transmitter
        # have the same Time Lag and Frequency
        """Return the current value."""
        wavelength = speed_of_light / self.__elements[0].Frequency
        return (wavelength / self.__elements[0].TimeLag) * 2.0 * np.pi

    def set(self, value: float):
        """
        Set the current value.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        wavelength = speed_of_light / self.__elements[0].Frequency
        for e in self.__elements:
            e.TimeLag = wavelength * value / (2.0 * np.pi)

    def set_and_wait(self, value: float):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the value unit."""
        return "rad"


# ------------------------------------------------------------------------------


class RWRFFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a simulator.
    """

    def __init__(self, elements: list[at.Element], harmonics: list[float]):
        """
        Initialize the RWRFFrequencyScalar.

        Parameters
        ----------
        elements : list[at.Element]
            Input value for this operation.
        harmonics : list[float]
            Input value for this operation.
        """
        self.__elements = elements
        self.__harm = harmonics

    def get(self) -> float:
        # Serialized cavity has the same frequency
        """Return the current value."""
        return self.__elements[0].Frequency

    def set(self, value: float):
        """
        Set the current value.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        for idx, e in enumerate(self.__elements):
            e.Frequency = value * self.__harm[idx]

    def set_and_wait(self, value: float):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the value unit."""
        return "Hz"


# ------------------------------------------------------------------------------


class RWRFATFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Provide read/write access to simulated RF frequency through AT methods.

    The accessor delegates frequency reads and writes to
    ``Lattice.get_rf_frequency`` and ``Lattice.set_rf_frequency``.
    """

    def __init__(self, ring: at.Lattice):
        """
        Initialize an Accelerator Toolbox RF-frequency accessor.

        Parameters
        ----------
        ring : at.Lattice
            Accelerator Toolbox lattice whose RF frequency is accessed.
        """
        self.__ring = ring

    def get(self) -> float:
        """Return the current value."""
        return self.__ring.get_rf_frequency()

    def set(self, value: float):
        """
        Set the current value.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        self.__ring.set_rf_frequency(value)

    def set_and_wait(self, value: float):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the value unit."""
        return "Hz"


# ------------------------------------------------------------------------------


class RWRFATotalVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Provide read/write access to total simulated RF voltage.

    The accessor delegates to the Accelerator Toolbox lattice methods
    ``get_rf_voltage`` and ``set_rf_voltage``.
    """

    def __init__(self, ring: at.Lattice):
        """
        Initialize an Accelerator Toolbox RF-voltage accessor.

        Parameters
        ----------
        ring : at.Lattice
            Accelerator Toolbox lattice whose total RF voltage is accessed.
        """
        self.__ring = ring

    def get(self) -> float:
        """Return the current value."""
        return self.__ring.get_rf_voltage()

    def set(self, value: float):
        """
        Set the current value.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        self.__ring.set_rf_voltage(value)

    def set_and_wait(self, value: float):
        """
        Set the value and wait for readback convergence.

        Parameters
        ----------
        value : float
            Input value for this operation.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the value unit."""
        return "V"


# ------------------------------------------------------------------------------


class RBetatronTuneArray(abstract.ReadFloatArray):
    """
    Class providing read-only access to the betatron tune of a ring.
    """

    def __init__(self, ring: at.Lattice):
        """
        Initialize the RBetatronTuneArray.

        Parameters
        ----------
        ring : at.Lattice
            Input value for this operation.
        """
        self.__ring = ring

    def get(self) -> float:
        """Return the current value."""
        return self.__ring.get_tune()[:2]

    def unit(self) -> str:
        """Return the value unit."""
        return "1"


# ------------------------------------------------------------------------------
