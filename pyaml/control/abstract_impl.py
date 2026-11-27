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
from ..common.units import SI_ANGLE, SI_FREQUENCY, SI_POSITION, SI_TUNE, SI_VOLTAGE, common_unit
from ..control.deviceaccess import DeviceAccess
from ..control.deviceaccesslist import DeviceAccessList
from ..control.si_deviceaccess import control_system_unit_of
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

    Methods
    -------
    add_devices(devices)
        Add one or more devices to the scalar aggregator.
    set(value)
        Write scalar values to the managed control-system devices.
    set_and_wait(value)
        Set values and wait for readback confirmation.
    get()
        Read the current values from all managed devices.
    readback()
        Read the last available values from all managed devices.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    nb_device()
        Return the number of managed devices.
    """

    def __init__(self, devs: DeviceAccessList):
        """
        Initialize the CSScalarAggregator.
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

    def unit(self) -> str | list[str] | None:
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return common_unit(self._devs.unit())

    def control_system_unit(self) -> str | list[str | None] | None:
        """Return the control-system unit for this quantity."""
        return common_unit(self._devs.control_system_unit())

    def nb_device(self) -> int:
        """Return the number of managed devices."""
        return self._devs.len()


# ------------------------------------------------------------------------------


class CSSparseScalarAggregator(CSScalarAggregator):
    """
    Scalar aggregator whose slots may have no device.

    Only existing devices are added to the backend aggregator, so they are
    still read in one grouped call. Values are scattered back to their slots
    and missing slots read NaN.

    Parameters
    ----------
    devs : DeviceAccessList
        Backend aggregator holding the existing devices.

    Methods
    -------
    add_devices(devices)
        Add one or more slots, ``None`` for a slot without device.
    set(value)
        Write the values of the slots that have a device.
    set_and_wait(value)
        Write the values of the slots that have a device and wait.
    get()
        Read all slots, NaN for slots without device.
    readback()
        Read all slot readbacks, NaN for slots without device.
    nb_device()
        Return the number of slots.
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(self, devs: DeviceAccessList):
        """
        Initialize the CSSparseScalarAggregator.
        """
        super().__init__(devs)
        self._nb_slots = 0
        self._slots: list[int] = []

    def add_devices(self, devices: DeviceAccess | None | list[DeviceAccess | None]):
        """
        Add one or more slots, ``None`` for a slot without device.

        Parameters
        ----------
        devices : DeviceAccess | None | list[DeviceAccess | None]
            Control-system device or devices to manage.
        """
        for d in devices if isinstance(devices, list) else [devices]:
            if d is not None:
                self._devs.add_devices(d)
                self._slots.append(self._nb_slots)
            self._nb_slots += 1

    def _scatter(self, values: NDArray[np.float64]) -> NDArray[np.float64]:
        out = np.full(self._nb_slots, np.nan)
        out[self._slots] = values
        return out

    def set(self, value: NDArray[np.float64]):
        """Write the values of the slots that have a device."""
        if self._slots:
            self._devs.set(np.asarray(value)[self._slots])

    def set_and_wait(self, value: NDArray[np.float64]):
        """Write the values of the slots that have a device and wait."""
        if self._slots:
            self._devs.set_and_wait(np.asarray(value)[self._slots])

    def get(self) -> NDArray[np.float64]:
        """Read all slots, NaN for slots without device."""
        return self._scatter(self._devs.get() if self._slots else [])

    def readback(self) -> np.array:
        """Read all slot readbacks, NaN for slots without device."""
        return self._scatter(self._devs.readback() if self._slots else [])

    def nb_device(self) -> int:
        """Return the number of slots."""
        return self._nb_slots

    def control_system_unit(self) -> str | list[str | None] | None:
        """Return the control-system unit for this quantity."""
        out: list[str | None] = [None] * self._nb_slots
        for slot, u in zip(self._slots, self._devs.control_system_unit(), strict=True):
            out[slot] = u
        return common_unit(out)


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

    Methods
    -------
    add_magnet(magnet, devs)
        Register a magnet and its hardware devices with the aggregator.
    set(value)
        Convert strengths to hardware values and write the setpoints.
    set_and_wait(value)
        Set magnet strengths and wait for hardware readback.
    get()
        Read the current values from the underlying devices.
    readback()
        Read back magnet strengths from measured hardware values.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(self, peer: CSScalarAggregator):
        """
        Initialize the CSStrengthScalarAggregator.
        """
        CSScalarAggregator.__init__(self, peer._devs)
        self.__models: list[MagnetModel] = []  # List of magnet model
        self.__modelToMagnet: list[list[tuple[int, int | None]]] = []  # strengths indexing
        self.__families: dict[int, Any] = {}  # model index -> strength accessor of a serialized family
        self.__nbMagnet = 0  # Number of magnet strengths
        self.__units: list[str] = []  # Strength unit of each magnet

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
        # Magnets of a serialized group share the serialized model (one power supply for N strengths):
        # the power-supply current is computed by the model from the strengths of the magnets present in the array,
        # the others following the resulting current. A serialized family has no series index: its value is the
        # average strength of the series, converted by the family strength accessor.
        if magnet.model.shares_power_supply():
            strengthIndex = magnet.series_index
        else:
            strengthIndex = magnet.strength.index() if isinstance(magnet.strength, abstract.RWMapper) else 0
        if magnet.model not in self.__models:
            index = len(self.__models)
            self.__models.append(magnet.model)
            self.__modelToMagnet.append([(self.__nbMagnet, strengthIndex)])
            self._devs.add_devices(devs)
        else:
            index = self.__models.index(magnet.model)
            self.__modelToMagnet[index].append((self.__nbMagnet, strengthIndex))
        self.__units.append(magnet.strength.unit())
        if strengthIndex is None:
            # MagnetArray guarantees that a family is never registered together with one of its magnets
            self.__families[index] = magnet.strength
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
            current = allHardwareValues[hardwareIndex : hardwareIndex + nbDev]
            if modelIndex in self.__families:
                [(valueIdx, _)] = self.__modelToMagnet[modelIndex]
                newHardwareValues[hardwareIndex] = self.__families[modelIndex].hardware_from_strength(
                    value[valueIdx], current[0]
                )
            else:
                requested = {strengthIdx: value[valueIdx] for valueIdx, strengthIdx in self.__modelToMagnet[modelIndex]}
                newHardwareValues[hardwareIndex : hardwareIndex + nbDev] = model.compute_hardware_values_partial(
                    current, requested
                )
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
        return self.__strengths_from_hardware(self._devs.get())  # Read all hardware setpoints

    def __strengths_from_hardware(self, allHardwareValues: NDArray[np.float64]) -> NDArray[np.float64]:
        """Convert the hardware values of every registered device to the strength of every registered magnet."""
        allStrength = np.zeros(self.__nbMagnet)
        hardwareIndex = 0
        for modelIndex, model in enumerate(self.__models):
            nbDev = len(model.get_device_names())
            hardware = allHardwareValues[hardwareIndex : hardwareIndex + nbDev]
            if modelIndex in self.__families:
                [(valueIdx, _)] = self.__modelToMagnet[modelIndex]
                allStrength[valueIdx] = self.__families[modelIndex].strength_from_hardware(hardware[0])
            else:
                mStrengths = model.compute_strengths(hardware)
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
        return self.__strengths_from_hardware(self._devs.readback())  # Read all hardware readback

    def unit(self) -> str | list[str] | None:
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return common_unit(self.__units)

    def control_system_unit(self) -> str | list[str] | None:
        """
        Return the control-system unit for this quantity.

        Same as unit(): no control-system device holds these values.
        """
        return self.unit()


class CSHardwareScalarAggregator(CSScalarAggregator):
    """
    Aggregate magnet hardware values, writing the power supply of a series once.

    Each registered magnet has one value. The magnets of a series share one power-supply device, added once: it gets
    the hardware value computed by the model of the series from the values of the magnets of the series present in the
    aggregator, and its value is read back for each of them.

    Parameters
    ----------
    peer : CSScalarAggregator
        Scalar device aggregator receiving the hardware devices.

    Methods
    -------
    add_magnet(magnet, dev)
        Register a magnet and the device holding its hardware value.
    set(value)
        Write the hardware value of every registered magnet.
    set_and_wait(value)
        Set the hardware values and wait for hardware readback.
    get()
        Return the hardware value of every registered magnet.
    readback()
        Return the hardware readback of every registered magnet.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    nb_device()
        Return the number of registered magnets.
    """

    def __init__(self, peer: CSScalarAggregator):
        """
        Initialize the CSHardwareScalarAggregator.
        """
        CSScalarAggregator.__init__(self, peer._devs)
        self.__slotToDevice: list[int] = []  # device index of each registered magnet
        self.__deviceOfSeries: dict[int, int] = {}  # id of a series model -> device index
        self.__series: list[tuple[MagnetModel, list[tuple[int, int]]] | None] = []  # per device: model, (slot, index)

    def add_magnet(self, magnet: Magnet, dev: DeviceAccess):
        """
        Register a magnet and the device holding its hardware value.

        Parameters
        ----------
        magnet : Magnet
            Magnet whose hardware value is aggregated.
        dev : DeviceAccess
            Device holding the hardware value of the magnet.
        """
        slot = len(self.__slotToDevice)
        series_index = magnet.series_index
        if series_index is None:
            device = self.__add_device(dev, None)
        else:
            device = self.__deviceOfSeries.get(id(magnet.model))
            if device is None:
                device = self.__add_device(dev, magnet.model)
                self.__deviceOfSeries[id(magnet.model)] = device
            self.__series[device][1].append((slot, series_index))
        self.__slotToDevice.append(device)

    def __add_device(self, dev: DeviceAccess, model: MagnetModel | None) -> int:
        self._devs.add_devices(dev)
        self.__series.append(None if model is None else (model, []))
        return len(self.__series) - 1

    def __device_values(self, value: NDArray[np.float64]) -> NDArray[np.float64]:
        """Return the value to write to each device from the value of each registered magnet."""
        value = np.asarray(value, dtype=float)
        if value.ndim == 0:
            value = np.full(len(self.__slotToDevice), float(value))
        deviceValues = np.zeros(len(self.__series))
        for slot, device in enumerate(self.__slotToDevice):
            if self.__series[device] is None:
                deviceValues[device] = value[slot]
        for device, series in enumerate(self.__series):
            if series is not None:
                model, members = series
                deviceValues[device] = model.compute_hardware_from_hardwares({idx: value[slot] for slot, idx in members})
        dev_range = self._devs.get_range()
        if not check_range(deviceValues, dev_range):
            raise PyAMLException(format_out_of_range_message(deviceValues, self._devs))
        return deviceValues

    def set(self, value: NDArray[np.float64]):
        """
        Write the hardware value of every registered magnet.

        Parameters
        ----------
        value : NDArray[np.float64]
            Hardware value of each registered magnet, in registration order. A scalar is applied to every magnet.

        Raises
        ------
        PyAMLException
            If a value to write is outside the range of its device. Nothing is written.
        """
        self._devs.set(self.__device_values(value))

    def set_and_wait(self, value: NDArray[np.float64]):
        """
        Set the hardware values and wait for hardware readback.

        Parameters
        ----------
        value : NDArray[np.float64]
            Hardware value of each registered magnet, in registration order.
        """
        self._devs.set_and_wait(self.__device_values(value))

    def get(self) -> NDArray[np.float64]:
        """Return the hardware value of every registered magnet."""
        return np.asarray(self._devs.get())[self.__slotToDevice]

    def readback(self) -> np.array:
        """Return the hardware readback of every registered magnet."""
        return np.asarray(self._devs.readback())[self.__slotToDevice]

    def unit(self) -> str | list[str] | None:
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        units = self._devs.unit()
        return common_unit([units[device] for device in self.__slotToDevice])

    def control_system_unit(self) -> str | list[str | None] | None:
        """Return the control-system unit for this quantity."""
        units = self._devs.control_system_unit()
        return common_unit([units[device] for device in self.__slotToDevice])

    def nb_device(self) -> int:
        """Return the number of registered magnets."""
        return len(self.__slotToDevice)


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

    Methods
    -------
    get()
        Return the current hardware setpoint.
    set(value)
        Validate and write a magnet hardware setpoint.
    set_and_wait(value)
        Set the hardware value and wait for readback confirmation.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    set_magnet_rigidity(brho)
        Set the beam rigidity used by the magnet model.
    """

    def __init__(self, model: MagnetModel, dev: DeviceAccess):
        """
        Initialize the RWHardwareScalar.
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
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return self.__model.get_hardware_units()[0]

    def control_system_unit(self) -> str | None:
        """Return the control-system unit for this quantity."""
        return control_system_unit_of(self.__dev)

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

    Methods
    -------
    get()
        Read the hardware value and convert it to magnet strength.
    set(value)
        Convert and write a magnet strength setpoint.
    set_and_wait(value)
        Set a magnet strength and wait for readback confirmation.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    set_magnet_rigidity(brho)
        Set the beam rigidity used by the magnet model.
    """

    def __init__(self, model: MagnetModel, dev: DeviceAccess):
        """
        Initialize the RWStrengthScalar.
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
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
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


class RWStrengthTrim(RWStrengthScalar):
    """Expose the incremental strength produced by a trim power supply.

    For the member magnet's excitation model ``f``, the trim strength is
    ``f(I + trim_factor * I_trim) - f(I)``. Setting that strength changes only
    the trim supply; the main current is read once per operation.

    Parameters
    ----------
    model : MagnetModel
        Single-magnet model converting equivalent main-coil current to strength.
    main_dev : DeviceAccess
        Main power-supply current device, used only for reading.
    trim_dev : DeviceAccess
        Physical trim-current device, used for reading and writing.
    trim_factor : float
        Nonzero signed factor converting physical trim current to equivalent
        main-coil current. Defaults to 1.0.

    Notes
    -----
    Conversion and inversion use the supplied model's existing behavior.
    Device limits apply to the physical trim current. Hardware access can use
    the existing ``RWHardwareScalar`` bound to ``trim_dev``.
    """

    def __init__(self, model: MagnetModel, main_dev: DeviceAccess, trim_dev: DeviceAccess, trim_factor: float = 1.0):
        if trim_factor == 0:
            raise ValueError("trim_factor must be nonzero")
        super().__init__(model, trim_dev)
        self.__model = model
        self.__main_dev = main_dev
        self.__trim_dev = trim_dev
        self.__trim_factor = trim_factor

    def get(self) -> float:
        """Return the trim contribution at the current main-supply setpoint."""
        main_current = self.__main_dev.get()
        trim_current = self.__trim_dev.get()
        main_strength = self.__model.compute_strengths([main_current])[0]
        total_strength = self.__model.compute_strengths([main_current + self.__trim_factor * trim_current])[0]
        return total_strength - main_strength

    def set(self, value: float):
        """Convert incremental strength and write only the trim supply.

        Raise PyAMLException when the calculated physical trim current is
        outside the trim device's configured range.
        """
        main_current = self.__main_dev.get()
        main_strength = self.__model.compute_strengths([main_current])[0]
        total_current = self.__model.compute_hardware_values([main_strength + value])[0]
        trim_current = (total_current - main_current) / self.__trim_factor
        if not check_range(trim_current, self.__trim_dev.get_range()):
            raise PyAMLException(format_out_of_range_message(trim_current, self.__trim_dev))
        self.__trim_dev.set(trim_current)


class RWSerializedStrengthScalar(RWStrengthScalar):
    """
    Expose the strength of one magnet of a serialized group.

    All magnets of a serialized group share one power supply. This accessor
    reads with the magnet's own sub-model, writes through the model of the
    series, and remembers the magnet position in the group so that aggregators
    can map it to the right strength of the serialized model.

    Parameters
    ----------
    model : MagnetModel
        Sub-model of the magnet, used for strength reading and units.
    dev : DeviceAccess
        Power-supply device shared by the serialized group.
    idx : int
        Zero-based position of the magnet in the serialized group.
    series_model : MagnetModel
        Model of the series, used to convert the strength of the magnet to the shared hardware value.

    Methods
    -------
    index()
        Return the position of the magnet in the serialized group.
    set(value)
        Set the shared hardware value giving the requested strength of the magnet.
    """

    def __init__(self, model: MagnetModel, dev: DeviceAccess, idx: int, series_model: MagnetModel):
        """
        Initialize the RWSerializedStrengthScalar.
        """
        super().__init__(model, dev)
        self.__dev = dev
        self.__idx = idx
        self.__series_model = series_model

    def index(self) -> int:
        """Return the position of the magnet in the serialized group."""
        return self.__idx

    def set(self, value: float):
        """
        Set the shared hardware value giving the requested strength of the magnet.

        The model of the series solves for the hardware value from the present one, so that the power supply does not
        move when it already gives the requested strength (for example on a plateau of the excitation curve).

        Parameters
        ----------
        value : float
            Strength of the magnet.

        Raises
        ------
        PyAMLException
            If the converted hardware value is outside the device's configured range.
        """
        current_hardware = np.array([self.__dev.get()])
        current = self.__series_model.compute_hardware_values_partial(current_hardware, {self.__idx: value})[0]
        dev_range = self.__dev.get_range()
        if not check_range(current, dev_range):
            raise PyAMLException(format_out_of_range_message(current, self.__dev))
        self.__dev.set(current)


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

    Methods
    -------
    get()
        Return the current hardware values in device order.
    set(value)
        Validate and write hardware values for all devices.
    set_and_wait(value)
        Set hardware values and wait for readback confirmation.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(self, model: MagnetModel, devs: list[DeviceAccess]):
        """
        Initialize the RWHardwareArray.
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
    def unit(self) -> str | list[str]:
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return common_unit(self.__model.get_hardware_units())

    def control_system_unit(self) -> str | list[str | None] | None:
        """Return the control-system unit for this quantity."""
        return common_unit([control_system_unit_of(d) for d in self.__devs])


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

    Methods
    -------
    get()
        Read hardware values and convert them to magnet strengths.
    set(value)
        Convert strengths to hardware values and write the setpoints.
    set_and_wait(value)
        Set magnet strengths and wait for readback confirmation.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    """

    def __init__(self, model: MagnetModel, devs: list[DeviceAccess]):
        """
        Initialize the RWStrengthArray.
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
    def unit(self) -> str | list[str]:
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return common_unit(self.__model.get_strength_units())


# ------------------------------------------------------------------------------


class RBpmArray(abstract.ReadFloatArray):
    """
    Expose horizontal and vertical BPM positions as an array.

    Parameters
    ----------
    hDev : DeviceAccess | None
        Device providing the horizontal BPM position, ``None`` for a BPM
        without horizontal plane.
    vDev : DeviceAccess | None
        Device providing the vertical BPM position, ``None`` for a BPM
        without vertical plane.

    Methods
    -------
    get()
        Return horizontal and vertical BPM positions (NaN for a missing plane).
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(self, hDev: DeviceAccess | None, vDev: DeviceAccess | None):
        """
        Initialize the RBpmArray.
        """
        self._hDev = hDev
        self._vDev = vDev

    def get(self) -> np.array:
        """Return horizontal and vertical BPM positions (NaN for a missing plane)."""
        return np.array([d.get() if d is not None else np.nan for d in (self._hDev, self._vDev)], dtype=float)

    def unit(self) -> str:
        """Return the pyAML unit for this quantity, i.e. returned by get()."""
        return SI_POSITION

    def control_system_unit(self) -> str | list[str | None] | None:
        """Return the control-system unit for this quantity."""
        return common_unit([control_system_unit_of(d) for d in (self._hDev, self._vDev)])


# ------------------------------------------------------------------------------


class RWBpmTiltScalar(abstract.ReadFloatScalar):
    """
    Class providing read access to a BPM tilt of a control system

    Parameters
    ----------
    dev : DeviceAccess
        Device handle giving access to the BPM tilt attribute.

    Methods
    -------
    get()
        Return horizontal and vertical BPM positions.
    set(value)
        Write the BPM tilt value to the control-system device.
    set_and_wait(value)
        Set the BPM tilt and wait for readback confirmation.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(self, dev: DeviceAccess):
        """
        Initialize the RWBpmTiltScalar.
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
            BPM tilt in rad.
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
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return SI_ANGLE

    def control_system_unit(self) -> str | None:
        """Return the control-system unit for this quantity."""
        return control_system_unit_of(self._dev)


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

    Methods
    -------
    get()
        Return horizontal and vertical BPM offsets.
    set(value)
        Write horizontal and vertical BPM offsets.
    set_and_wait(value)
        Set BPM offsets and wait for readback confirmation.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(self, hDev: DeviceAccess, vDev: DeviceAccess):
        """
        Initialize the RWBpmOffsetArray.
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

    def unit(self) -> str:
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return SI_POSITION

    def control_system_unit(self) -> str | list[str | None] | None:
        """Return the control-system unit for this quantity."""
        return common_unit([control_system_unit_of(d) for d in (self._hDev, self._vDev)])


# ------------------------------------------------------------------------------


class RWRFVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity voltage
    for a transmitter of a control system.

    Parameters
    ----------
    transmitter : RFTransmitter
        RF transmitter whose configuration supplies the voltage unit.
    dev : DeviceAccess
        Control-system device holding the cavity-voltage value.

    Methods
    -------
    get()
        Return the current cavity voltage.
    set(value)
        Write a cavity-voltage setpoint to the transmitter device.
    set_and_wait(value)
        Set the cavity voltage and wait for readback confirmation.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(self, transmitter: RFTransmitter, dev: DeviceAccess):
        """
        Initialize the RWRFVoltageScalar.
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
            Cavity-voltage setpoint in V.
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
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return SI_VOLTAGE

    def control_system_unit(self) -> str | None:
        """Return the control-system unit for this quantity."""
        return control_system_unit_of(self.__dev)


# ------------------------------------------------------------------------------


class RWRFPhaseScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity phase
    for a transmitter of a control system.

    Parameters
    ----------
    transmitter : RFTransmitter
        RF transmitter whose configuration supplies the phase unit.
    dev : DeviceAccess
        Control-system device holding the cavity phase.

    Methods
    -------
    get()
        Return the current cavity phase.
    set(value)
        Write a cavity-phase setpoint to the transmitter device.
    set_and_wait(value)
        Set the cavity phase and wait for readback confirmation.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(self, transmitter: RFTransmitter, dev: DeviceAccess):
        """
        Initialize the RWRFPhaseScalar.
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
            Cavity-phase setpoint in rad.
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
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return SI_ANGLE

    def control_system_unit(self) -> str | None:
        """Return the control-system unit for this quantity."""
        return control_system_unit_of(self.__dev)


# ------------------------------------------------------------------------------


class RWRFFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a control system.

    Parameters
    ----------
    rf : RFPlant
        RF plant whose configuration supplies the frequency unit.
    dev : DeviceAccess
        Control-system device holding the RF frequency.

    Methods
    -------
    get()
        Return the current RF frequency.
    set(value)
        Write an RF-frequency setpoint to the plant device.
    set_and_wait(value)
        Set the RF frequency and wait for readback confirmation.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(self, rf: RFPlant, dev: DeviceAccess):
        """
        Initialize the RWRFFrequencyScalar.
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
            RF-frequency setpoint in Hz.
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
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return SI_FREQUENCY

    def control_system_unit(self) -> str | None:
        """Return the control-system unit for this quantity."""
        return control_system_unit_of(self.__dev)


# ------------------------------------------------------------------------------


class RBetatronTuneArray(abstract.ReadFloatArray):
    """
    Expose horizontal and vertical betatron tunes as a read-only array.

    A plane whose device reports a frequency ``f`` is converted to the
    fractional tune.

    Parameters
    ----------
    devs : list[DeviceAccess]
        Devices providing horizontal and vertical tune measurements, in tune
        units or in Hz.
    is_frequency : list[bool] or None, optional
        ``[horizontal, vertical]`` flags, ``True`` for a device read in Hz.
    above_half : list[bool] or None, optional
        ``[horizontal, vertical]`` flags, ``True`` when the fractional tune of
        a plane read in Hz is above the half-integer.
    revolution_frequency : callable or None, optional
        Returns the revolution frequency in Hz, called on every ``get()``
        when a plane is read in Hz.

    Methods
    -------
    get()
        Return horizontal and vertical betatron tunes.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get().
    control_system_unit()
        Return the control-system unit for this quantity.
    """

    def __init__(
        self,
        devs: list[DeviceAccess],
        is_frequency: list[bool] | None = None,
        above_half: list[bool] | None = None,
        revolution_frequency=None,
    ):
        """
        Initialize the RBetatronTuneArray.
        """
        self.__devs = devs
        self.__is_frequency = np.array(is_frequency if is_frequency is not None else [False, False], dtype=bool)
        self.__above_half = np.array(above_half if above_half is not None else [False, False], dtype=bool)
        self.__revolution_frequency = revolution_frequency

    def get(self) -> NDArray:
        """Return horizontal and vertical betatron tunes."""
        values = np.array([d.get() for d in self.__devs], dtype=float)
        if self.__is_frequency.any():
            if self.__revolution_frequency is None:
                raise PyAMLException("Tune devices read in Hz need a revolution frequency")
            q = np.mod(values / self.__revolution_frequency(), 1.0)  # Sidebands (n ± q) f_rev
            q = np.minimum(q, 1.0 - q)  # Fold into [0, 0.5]
            q = np.where(self.__above_half, 1.0 - q, q)
            values = np.where(self.__is_frequency, q, values)
        return values

    def unit(self) -> str:
        """Return the pyAML unit for this quantity, i.e. returned by get()."""
        return SI_TUNE

    def control_system_unit(self) -> str | list[str | None] | None:
        """Return the control-system unit for this quantity."""
        return common_unit([control_system_unit_of(d) for d in self.__devs])


# ------------------------------------------------------------------------------
