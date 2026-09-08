"""
Control-system implementations of PyAML read/write interfaces.

The classes in this module adapt control-system devices to PyAML scalar and
array interfaces, including conversions between hardware values, magnet
strengths, BPM readings, and RF quantities.
"""

from typing import Any

import numpy as np
from numpy import double
from numpy.typing import NDArray

from .. import PyAMLException
from ..common import abstract
from ..common.abstract_aggregator import ScalarAggregator
from ..control.deviceaccess import DeviceAccess
from ..control.deviceaccesslist import DeviceAccessList
from ..magnet.magnet import Magnet
from ..magnet.model import MagnetModel
from ..rf.rf_plant import RFPlant
from ..rf.rf_transmitter import RFTransmitter

# ------------------------------------------------------------------------------


def check_range(values: Any, dev_range: Any) -> bool:
    """
    Check whether values are within given ranges.

    Inverted semantics:
        - True  -> all checks pass (everything is within bounds)
        - False -> at least one check fails (out of range)

    dev_range format (flat):
        [min1, max1, min2, max2, ...]

    Broadcasting rules:
        Let N = number of values, K = number of ranges (pairs).
        - N == K           : one range per value
        - N == 1 and K > 1: the single value must satisfy ALL ranges
        - N > 1 and K == 1: the single range applies to ALL values
    """
    # ---- Normalize values to a 1D float array ----
    v = np.asarray(values, dtype=float)
    if v.ndim == 0:
        v = v.reshape(1)
    else:
        v = v.ravel()
    n = v.size

    # ---- Normalize dev_range (object to preserve None) ----
    r = np.asarray(dev_range, dtype=object).ravel()
    if (r.size % 2) != 0:
        raise ValueError(f"dev_range must have an even length, got {r.size}")

    mins_obj = r[0::2]
    maxs_obj = r[1::2]
    k = mins_obj.size

    # ---- Broadcasting rules ----
    if n == k:
        vv = v
        mins = mins_obj
        maxs = maxs_obj
    elif n == 1 and k > 1:
        vv = np.full(k, v[0], dtype=float)
        mins = mins_obj
        maxs = maxs_obj
    elif n > 1 and k == 1:
        vv = v
        mins = np.full(n, mins_obj[0], dtype=object)
        maxs = np.full(n, maxs_obj[0], dtype=object)
    else:
        raise ValueError(f"Inconsistent sizes: {n} value(s) for {k} range(s). Supported: N==K, N==1, or K==1.")

    # ---- Replace None bounds with -inf / +inf (NumPy-safe) ----
    mins_is_none = np.equal(mins, None)
    maxs_is_none = np.equal(maxs, None)

    mins_f = np.where(mins_is_none, -np.inf, mins).astype(float)
    maxs_f = np.where(maxs_is_none, +np.inf, maxs).astype(float)

    # ---- Vectorized range check ----
    return bool(np.all((vv >= mins_f) & (vv <= maxs_f)))


def _as_1d_float_array(values: Any) -> np.ndarray:
    """
    Convert scalar or array-like values to a one-dimensional float array.

    Parameters
    ----------
    values : object
        Scalar or array-like values to normalize.

    Returns
    -------
    numpy.ndarray
        One-dimensional array with ``float`` dtype.
    """
    v = np.asarray(values, dtype=float)
    if v.ndim == 0:
        return v.reshape(1)
    return v.ravel()


def _iter_devices_and_ranges(devs: DeviceAccess | DeviceAccessList):
    """
    Return each device together with its inclusive hardware range.

    Works for:
      - DeviceAccess: yields 1 item
      - DeviceAccessList: yields N items based on get_devices() and get_range() flattening

    Parameters
    ----------
    devs : DeviceAccess or DeviceAccessList
        Device or device collection whose ranges should be inspected.

    Returns
    -------
    list of tuple
        Pairs containing a device and its ``[minimum, maximum]`` range.
    """
    # Single device
    if isinstance(devs, DeviceAccess):
        r = devs.get_range()
        if r is None:
            r = [None, None]
        return [(devs, [r[0], r[1]])]

    # get_range() return a flat list
    flat = devs.get_range()
    if (len(flat) % 2) != 0:
        raise ValueError(f"dev_range must have an even length, got {flat.size}")

    # Reshape
    pairs = []
    for i, dev in enumerate(devs):
        pairs.append((dev, [flat[2 * i], flat[2 * i + 1]]))
    return pairs


def format_out_of_range_message(
    values: Any,
    devs: DeviceAccess | DeviceAccessList,
    *,
    header: str = "Values out of range:",
) -> str:
    """
    Build a user-friendly error message for out-of-range values.

    Output example:
        Values out of range:
        110 A, '//host/dev/attr' [10.0, 109.0]
        110 A, '//host/dev/attr' [10.0, 109.0]

    Notes:
      - Only failing channels are listed.
      - Supports scalar/array values and DeviceAccess/DeviceAccessList.
      - Uses check_range() semantics (inclusive bounds, None => unbounded).
    """
    v = _as_1d_float_array(values)
    dev_pairs = _iter_devices_and_ranges(devs)

    # Apply the same broadcasting rules as check_range():
    # - N == K : value per device
    # - N == 1 and K > 1 : single value checked against all devices
    # - N > 1 and K == 1 : single device range applied to all values (rare here but supported)
    n = v.size
    k = len(dev_pairs)

    if n == k:
        vv = v
        pairs = dev_pairs
    elif n == 1 and k > 1:
        vv = np.full(k, v[0], dtype=float)
        pairs = dev_pairs
    elif n > 1 and k == 1:
        vv = v
        pairs = [dev_pairs[0]] * n
    else:
        raise ValueError(f"Inconsistent sizes: {n} value(s) for {k} device(s). Supported: N==K, N==1, or K==1.")

    lines = [header]
    for val, (dev, r) in zip(vv, pairs, strict=True):
        if not check_range(val, r):
            unit = dev.unit() if hasattr(dev, "unit") else ""
            name = str(dev)
            rmin, rmax = r[0], r[1]
            lines.append(f"{val:g} {unit}, '{name}' [{rmin}, {rmax}]")

    # Fallback if nothing selected (should not happen if caller checked range before)
    if len(lines) == 1:
        lines.append("(no channel details available)")

    return "\n".join(lines)


class CSScalarAggregator(ScalarAggregator):
    """
    Aggregate scalar control-system devices into one PyAML interface.

    Parameters
    ----------
    devs : DeviceAccessList
        Devices managed by the aggregator.
    """

    def __init__(self, devs: DeviceAccessList):
        """
        Initialize the CSScalarAggregator.

        Parameters
        ----------
        devs : DeviceAccessList
            Devices managed by the aggregator.
        """
        self._devs = devs

    def add_devices(self, devices: DeviceAccess | list[DeviceAccess]):
        """
        Add one or more devices to the scalar aggregator.

        Parameters
        ----------
        devices : DeviceAccess | list[DeviceAccess]
            Control-system device or devices to manage.
        """
        self._devs.add_devices(devices)

    def set(self, value: NDArray[np.float64]):
        """
        Write scalar values to the managed control-system devices.

        Parameters
        ----------
        value : NDArray[np.float64]
            Values to write, in the same order as the managed devices.
        """
        self._devs.set(value)

    def set_and_wait(self, value: NDArray[np.float64]):
        """
        Set values and wait for readback confirmation.

        This control-system implementation does not currently support
        waiting for device readback and raises :class:`NotImplementedError`.

        Parameters
        ----------
        value : NDArray[np.float64]
            Values that would be written to the managed devices.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous setpoint confirmation is not
            implemented.
        """
        self._devs.set_and_wait(value)

    def get(self) -> NDArray[np.float64]:
        """Read the current values from all managed devices."""
        return self._devs.get()

    def readback(self) -> np.array:
        """Read the last available values from all managed devices."""
        return self._devs.readback()

    def unit(self) -> str:
        """Return the unit reported by the managed devices."""
        return self._devs.unit()

    def nb_device(self) -> int:
        """Return the number of managed devices."""
        return self._devs.len()


# ------------------------------------------------------------------------------


class CSStrengthScalarAggregator(CSScalarAggregator):
    """
    Aggregate magnet strengths while avoiding duplicate hardware writes.

    Magnet models convert between exposed strengths and hardware setpoints.
    Shared models, such as those used by virtual magnets from combined-function
    magnets, are written only once per underlying power supply.

    Parameters
    ----------
    peer : CSScalarAggregator
        Scalar device aggregator containing the hardware devices.
    """

    def __init__(self, peer: CSScalarAggregator):
        """
        Initialize the CSStrengthScalarAggregator.

        Parameters
        ----------
        peer : CSScalarAggregator
            Scalar device aggregator containing the hardware devices.
        """
        CSScalarAggregator.__init__(self, peer._devs)
        self.__models: list[MagnetModel] = []  # List of magnet model
        self.__modelToMagnet: list[list[tuple[int, int]]] = []  # strengths indexing
        self.__nbMagnet = 0  # Number of magnet strengths

    def add_magnet(self, magnet: Magnet, devs: list[DeviceAccess]):
        # Incoming magnet can be a magnet exported from
        # a CombinedFunctionMagnet or simple magnet.
        # All magnets exported from a same CombinedFunctionMagnet share the same model
        # TODO: check that strength is supported (m.strength may be None)
        """
        Register a magnet and its hardware devices with the aggregator.

        Parameters
        ----------
        magnet : Magnet
            Magnet whose strength is being aggregated.
        devs : list[DeviceAccess]
            Hardware devices associated with the magnet model.
        """
        strengthIndex = magnet.strength.index() if isinstance(magnet.strength, abstract.RWMapper) else 0
        if magnet.model not in self.__models:
            index = len(self.__models)
            self.__models.append(magnet.model)
            self.__modelToMagnet.append([(self.__nbMagnet, strengthIndex)])
            self._devs.add_devices(devs)
        else:
            index = self.__models.index(magnet.model)
            self.__modelToMagnet[index].append((self.__nbMagnet, strengthIndex))
        self.__nbMagnet += 1

    def set(self, value: NDArray[np.float64]):
        """
        Convert strengths to hardware values and write the setpoints.

        Parameters
        ----------
        value : NDArray[np.float64]
            Magnet strengths, ordered according to the registered magnets.
        """
        allHardwareValues = self._devs.get()  # Read all hardware setpoints
        newHardwareValues = np.zeros(self.nb_device())
        hardwareIndex = 0
        for modelIndex, model in enumerate(self.__models):
            nbDev = len(model.get_device_names())
            mStrengths = model.compute_strengths(allHardwareValues[hardwareIndex : hardwareIndex + nbDev])
            for valueIdx, strengthIdx in self.__modelToMagnet[modelIndex]:
                mStrengths[strengthIdx] = value[valueIdx]
            newHardwareValues[hardwareIndex : hardwareIndex + nbDev] = model.compute_hardware_values(mStrengths)
            hardwareIndex += nbDev
        dev_range = self._devs.get_range()
        if not check_range(newHardwareValues, dev_range):
            raise PyAMLException(format_out_of_range_message(newHardwareValues, self._devs))
        self._devs.set(newHardwareValues)

    def set_and_wait(self, value: NDArray[np.float64]):
        """
        Set magnet strengths and wait for hardware readback.

        Waiting for readback is not implemented by this aggregator.

        Parameters
        ----------
        value : NDArray[np.float64]
            Magnet strengths to convert and write.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous confirmation is unsupported.
        """
        raise NotImplementedError("Not implemented yet.")

    def get(self) -> NDArray[np.float64]:
        """Read the current values from the underlying devices."""
        allHardwareValues = self._devs.get()  # Read all hardware setpoints
        allStrength = np.zeros(self.__nbMagnet)
        hardwareIndex = 0
        for modelIndex, model in enumerate(self.__models):
            nbDev = len(model.get_device_names())
            mStrengths = model.compute_strengths(allHardwareValues[hardwareIndex : hardwareIndex + nbDev])
            for valueIdx, strengthIdx in self.__modelToMagnet[modelIndex]:
                allStrength[valueIdx] = mStrengths[strengthIdx]
            hardwareIndex += nbDev
        return allStrength

    def readback(self) -> np.array:
        """
        Read back magnet strengths from measured hardware values.

        Returns
        -------
        numpy.ndarray
            Magnet strengths corresponding to the latest device readbacks.
        """
        allHardwareValues = self._devs.readback()  # Read all hardware readback
        allStrength = np.zeros(self.__nbMagnet)
        hardwareIndex = 0
        for modelIndex, model in enumerate(self.__models):
            nbDev = len(model.get_device_names())
            mStrengths = model.compute_strengths(allHardwareValues[hardwareIndex : hardwareIndex + nbDev])
            for valueIdx, strengthIdx in self.__modelToMagnet[modelIndex]:
                allStrength[valueIdx] = mStrengths[strengthIdx]
            hardwareIndex += nbDev
        return allStrength

    def unit(self) -> str:
        """Return the units associated with the underlying devices."""
        return self._devs.unit()


# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------


class RWHardwareScalar(abstract.ReadWriteFloatScalar):
    """
    Expose one magnet hardware setpoint as a readable/writable scalar.

    Parameters
    ----------
    model : MagnetModel
        Magnet model used to determine the hardware unit.
    dev : DeviceAccess
        Control-system device holding the hardware setpoint.
    """

    def __init__(self, model: MagnetModel, dev: DeviceAccess):
        """
        Initialize the RWHardwareScalar.

        Parameters
        ----------
        model : MagnetModel
            Magnet model used to determine the hardware unit.
        dev : DeviceAccess
            Control-system device holding the hardware setpoint.
        """
        self.__model = model
        self.__dev = dev

    def get(self) -> float:
        """Return the current hardware setpoint."""
        return self.__dev.get()

    def set(self, value: float):
        """
        Validate and write a magnet hardware setpoint.

        Parameters
        ----------
        value : float
            Hardware value to write to the control-system device.

        Raises
        ------
        PyAMLException
            If ``value`` is outside the device's configured range.
        """
        dev_range = self.__dev.get_range()
        if not check_range(value, dev_range):
            raise PyAMLException(format_out_of_range_message(value, self.__dev))
        self.__dev.set(value)

    def set_and_wait(self, value: double):
        """
        Set the hardware value and wait for readback confirmation.

        Parameters
        ----------
        value : double
            Hardware value to write.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous confirmation is unsupported.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the hardware unit defined by the magnet model."""
        return self.__model.get_hardware_units()[0]

    def set_magnet_rigidity(self, brho: np.double):
        """
        Set the beam rigidity used by the magnet model.

        Parameters
        ----------
        brho : np.double
            Magnetic rigidity in tesla metres.
        """
        self.__model.set_magnet_rigidity(brho)


# ------------------------------------------------------------------------------


class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Expose one magnet strength with hardware-value conversion.

    Parameters
    ----------
    model : MagnetModel
        Magnet model used for strength conversion and units.
    dev : DeviceAccess
        Control-system device holding the corresponding hardware value.
    """

    def __init__(self, model: MagnetModel, dev: DeviceAccess):
        """
        Initialize the RWStrengthScalar.

        Parameters
        ----------
        model : MagnetModel
            Magnet model used for strength conversion and units.
        dev : DeviceAccess
            Control-system device holding the corresponding hardware value.
        """
        self.__model = model
        self.__dev = dev

    # Gets the value
    def get(self) -> float:
        """Read the hardware value and convert it to magnet strength."""
        current = self.__dev.get()
        return self.__model.compute_strengths([current])[0]

    # Sets the value
    def set(self, value: float):
        """
        Convert and write a magnet strength setpoint.

        Parameters
        ----------
        value : float
            Magnet strength to convert to hardware units and write.

        Raises
        ------
        PyAMLException
            If the converted hardware value is outside the device's
            configured range.
        """
        current = self.__model.compute_hardware_values([value])[0]
        dev_range = self.__dev.get_range()
        if not check_range(current, dev_range):
            raise PyAMLException(format_out_of_range_message(current, self.__dev))
        self.__dev.set(current)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        """
        Set a magnet strength and wait for readback confirmation.

        Parameters
        ----------
        value : float
            Magnet strength to convert and write.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous confirmation is unsupported.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        """Return the strength unit defined by the magnet model."""
        return self.__model.get_strength_units()[0]

    def set_magnet_rigidity(self, brho: np.double):
        """
        Set the beam rigidity used by the magnet model.

        Parameters
        ----------
        brho : np.double
            Magnetic rigidity in tesla metres.
        """
        self.__model.set_magnet_rigidity(brho)


# ------------------------------------------------------------------------------


class RWHardwareArray(abstract.ReadWriteFloatArray):
    """
    Expose multiple magnet hardware setpoints as an array interface.

    Parameters
    ----------
    model : MagnetModel
        Magnet model defining the hardware units.
    devs : list[DeviceAccess]
        Control-system devices holding the hardware setpoints.
    """

    def __init__(self, model: MagnetModel, devs: list[DeviceAccess]):
        """
        Initialize the RWHardwareArray.

        Parameters
        ----------
        model : MagnetModel
            Magnet model defining the hardware units.
        devs : list[DeviceAccess]
            Control-system devices holding the hardware setpoints.
        """
        self.__model = model
        self.__devs = devs

    # Gets the value
    def get(self) -> np.array:
        """Return the current hardware values in device order."""
        return np.array([p.get() for p in self.__devs])

    # Sets the value
    def set(self, value: np.array):
        """
        Validate and write hardware values for all devices.

        Parameters
        ----------
        value : np.array
            Hardware values ordered to match ``self.__devs``.

        Raises
        ------
        PyAMLException
            If any value is outside its device's configured range.
        """
        for idx, p in enumerate(self.__devs):
            dev_range = p.get_range()
            if not check_range(value[idx], dev_range):
                raise PyAMLException(format_out_of_range_message(value[idx], p))
            p.set(value[idx])

    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        """
        Set hardware values and wait for readback confirmation.

        Parameters
        ----------
        value : np.array
            Hardware values to write in device order.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous confirmation is unsupported.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        """Return the hardware units defined by the magnet model."""
        return self.__model.get_hardware_units()


# ------------------------------------------------------------------------------


class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Expose multiple magnet strengths with hardware-value conversion.

    Parameters
    ----------
    model : MagnetModel
        Magnet model used for strength conversion and units.
    devs : list[DeviceAccess]
        Control-system devices corresponding to the model's hardware values.
    """

    def __init__(self, model: MagnetModel, devs: list[DeviceAccess]):
        """
        Initialize the RWStrengthArray.

        Parameters
        ----------
        model : MagnetModel
            Magnet model used for strength conversion and units.
        devs : list[DeviceAccess]
            Control-system devices corresponding to the model's hardware values.
        """
        self.__model = model
        self.__devs = devs

    # Gets the value
    def get(self) -> np.array:
        """Read hardware values and convert them to magnet strengths."""
        r = np.array([p.get() for p in self.__devs])
        str = self.__model.compute_strengths(r)
        return str

    # Sets the value
    def set(self, value: np.array):
        """
        Convert strengths to hardware values and write the setpoints.

        Parameters
        ----------
        value : np.array
            Magnet strengths ordered to match ``self.__devs``.
        """
        cur = self.__model.compute_hardware_values(value)
        for idx, p in enumerate(self.__devs):
            dev_range = p.get_range()
            if not check_range(cur[idx], dev_range):
                raise PyAMLException(format_out_of_range_message(cur[idx], p))

        for idx, p in enumerate(self.__devs):
            p.set(cur[idx])

    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        """
        Set magnet strengths and wait for readback confirmation.

        Parameters
        ----------
        value : np.array
            Magnet strengths to convert and write.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous confirmation is unsupported.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        """Return the strength units defined by the magnet model."""
        return self.__model.get_strength_units()


# ------------------------------------------------------------------------------


class RBpmArray(abstract.ReadFloatArray):
    """
    Expose horizontal and vertical BPM positions as an array.

    Parameters
    ----------
    hDev : DeviceAccess
        Device providing the horizontal BPM position.
    vDev : DeviceAccess
        Device providing the vertical BPM position.
    """

    def __init__(self, hDev: DeviceAccess, vDev: DeviceAccess):
        """
        Initialize the RBpmArray.

        Parameters
        ----------
        hDev : DeviceAccess
            Device providing the horizontal BPM position.
        vDev : DeviceAccess
            Device providing the vertical BPM position.
        """
        self._hDev = hDev
        self._vDev = vDev

    def get(self) -> np.array:
        """Return horizontal and vertical BPM positions."""
        return np.array([self._hDev.get(), self._vDev.get()])

    # Gets the unit of the value Assume that x and y, offsets and positions
    # have the same unit
    def unit(self) -> str:
        """Return the unit reported by the BPM device."""
        return self._hDev.unit()


# ------------------------------------------------------------------------------


class RWBpmTiltScalar(abstract.ReadFloatScalar):
    """
    Class providing read access to a BPM tilt of a control system
    """

    def __init__(self, dev: DeviceAccess):
        """
        Initialize the RWBpmTiltScalar.

        Parameters
        ----------
        dev : DeviceAccess
            Device handle giving access to the BPM tilt attribute.
        """
        self._dev = dev

    def get(self) -> float:
        """Return horizontal and vertical BPM positions."""
        return self._dev.get()

    def set(self, value: float):
        """
        Write the BPM tilt value to the control-system device.

        Parameters
        ----------
        value : float
            BPM tilt value in the device's configured units.
        """
        self._dev.set(value)

    def set_and_wait(self, value: NDArray[np.float64]):
        """
        Set the BPM tilt and wait for readback confirmation.

        Parameters
        ----------
        value : NDArray[np.float64]
            BPM tilt value to write.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous confirmation is unsupported.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        """Return the unit shared by the BPM devices."""
        return self._dev.unit()


# ------------------------------------------------------------------------------


class RWBpmOffsetArray(abstract.ReadWriteFloatArray):
    """
    Expose horizontal and vertical BPM offsets as a writable array.

    Parameters
    ----------
    hDev : DeviceAccess
        Device handle for the horizontal BPM offset.
    vDev : DeviceAccess
        Device handle for the vertical BPM offset.
    """

    def __init__(self, hDev: DeviceAccess, vDev: DeviceAccess):
        """
        Initialize the RWBpmOffsetArray.

        Parameters
        ----------
        hDev : DeviceAccess
            Device handle for the horizontal BPM offset.
        vDev : DeviceAccess
            Device handle for the vertical BPM offset.
        """
        self._hDev = hDev
        self._vDev = vDev

    def get(self) -> np.array:
        """Return horizontal and vertical BPM offsets."""
        return np.array([self._hDev.get(), self._vDev.get()])

    def set(self, value: NDArray[np.float64]):
        """
        Write horizontal and vertical BPM offsets.

        Parameters
        ----------
        value : NDArray[np.float64]
            Two-element array containing horizontal and vertical offsets.
        """
        self._hDev.set(value[0])
        self._vDev.set(value[1])

    def set_and_wait(self, value: NDArray[np.float64]):
        """
        Set BPM offsets and wait for readback confirmation.

        Parameters
        ----------
        value : NDArray[np.float64]
            Two-element array containing horizontal and vertical offsets.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous confirmation is unsupported.
        """
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value Assume that x and y, offsets and positions
    # have the same unit
    def unit(self) -> str:
        """Return the unit shared by the BPM offset devices."""
        return self._hDev.unit()


# ------------------------------------------------------------------------------


class RWRFVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity voltage
    for a transmitter of a control system.
    """

    def __init__(self, transmitter: RFTransmitter, dev: DeviceAccess):
        """
        Initialize the RWRFVoltageScalar.

        Parameters
        ----------
        transmitter : RFTransmitter
            RF transmitter whose configuration supplies the voltage unit.
        dev : DeviceAccess
            Control-system device holding the cavity-voltage value.
        """
        self.__transmitter = transmitter
        self.__dev = dev

    def get(self) -> float:
        """Return the current cavity voltage."""
        return self.__dev.get()

    def set(self, value: float):
        """
        Write a cavity-voltage setpoint to the transmitter device.

        Parameters
        ----------
        value : float
            Cavity-voltage setpoint in the configured voltage unit.
        """
        self.__dev.set(value)

    def set_and_wait(self, value: float):
        """
        Set the cavity voltage and wait for readback confirmation.

        Parameters
        ----------
        value : float
            Cavity-voltage setpoint.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous confirmation is unsupported.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the configured cavity-voltage unit."""
        return self.__transmitter._cfg.voltage.unit()


# ------------------------------------------------------------------------------


class RWRFPhaseScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity phase
    for a transmitter of a control system.
    """

    def __init__(self, transmitter: RFTransmitter, dev: DeviceAccess):
        """
        Initialize the RWRFPhaseScalar.

        Parameters
        ----------
        transmitter : RFTransmitter
            RF transmitter whose configuration supplies the phase unit.
        dev : DeviceAccess
            Control-system device holding the cavity phase.
        """
        self.__transmitter = transmitter
        self.__dev = dev

    def get(self) -> float:
        """Return the current cavity phase."""
        return self.__dev.get()

    def set(self, value: float):
        """
        Write a cavity-phase setpoint to the transmitter device.

        Parameters
        ----------
        value : float
            Cavity-phase setpoint in the configured phase unit.
        """
        self.__dev.set(value)

    def set_and_wait(self, value: float):
        """
        Set the cavity phase and wait for readback confirmation.

        Parameters
        ----------
        value : float
            Cavity-phase setpoint.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous confirmation is unsupported.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the configured cavity-phase unit."""
        return self.__transmitter._cfg.phase.unit()


# ------------------------------------------------------------------------------


class RWRFFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a control system.
    """

    def __init__(self, rf: RFPlant, dev: DeviceAccess):
        """
        Initialize the RWRFFrequencyScalar.

        Parameters
        ----------
        rf : RFPlant
            RF plant whose configuration supplies the frequency unit.
        dev : DeviceAccess
            Control-system device holding the RF frequency.
        """
        self.__rf = rf
        self.__dev = dev

    def get(self) -> float:
        # Serialized cavity has the same frequency
        """Return the current RF frequency."""
        return self.__dev.get()

    def set(self, value: float):
        """
        Write an RF-frequency setpoint to the plant device.

        Parameters
        ----------
        value : float
            RF-frequency setpoint in the configured frequency unit.
        """
        self.__dev.set(value)

    def set_and_wait(self, value: float):
        """
        Set the RF frequency and wait for readback confirmation.

        Parameters
        ----------
        value : float
            RF-frequency setpoint.

        Raises
        ------
        NotImplementedError
            Always raised because asynchronous confirmation is unsupported.
        """
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        """Return the configured RF-frequency unit."""
        return self.__rf._cfg.masterclock.unit()


# ------------------------------------------------------------------------------


class RBetatronTuneArray(abstract.ReadFloatArray):
    """
    Expose horizontal and vertical betatron tunes as a read-only array.

    Parameters
    ----------
    tune_monitor : object
        Tune monitor configuration supplying the tune unit.
    devs : list[DeviceAccess]
        Devices providing horizontal and vertical tune measurements.
    """

    def __init__(self, tune_monitor, devs: list[DeviceAccess]):
        """
        Initialize the RBetatronTuneArray.

        Parameters
        ----------
        tune_monitor : object
            Tune monitor configuration supplying the tune unit.
        devs : list[DeviceAccess]
            Devices providing horizontal and vertical tune measurements.
        """
        self.__tune_monitor = tune_monitor
        self.__devs = devs

    def get(self) -> NDArray:
        # Return horizontal and vertical betatron tunes as a NumPy array
        """Return horizontal and vertical betatron tunes."""
        return np.array(
            [
                self.__devs[0].get(),
                self.__devs[1].get(),
            ]
        )

    def unit(self) -> str:
        """Return the configured betatron-tune unit."""
        return self.__tune_monitor._cfg.tune_v.unit()


# ------------------------------------------------------------------------------
