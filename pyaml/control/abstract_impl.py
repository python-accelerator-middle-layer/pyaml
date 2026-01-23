from typing import Any

import numpy as np
from numpy import double
from numpy.typing import NDArray

from .. import PyAMLException
from ..bpm.bpm_model import BPMModel
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
        raise ValueError(
            f"Inconsistent sizes: {n} value(s) for {k} range(s). "
            f"Supported: N==K, N==1, or K==1."
        )

    # ---- Replace None bounds with -inf / +inf (NumPy-safe) ----
    mins_is_none = np.equal(mins, None)
    maxs_is_none = np.equal(maxs, None)

    mins_f = np.where(mins_is_none, -np.inf, mins).astype(float)
    maxs_f = np.where(maxs_is_none, +np.inf, maxs).astype(float)

    # ---- Vectorized range check ----
    return bool(np.all((vv >= mins_f) & (vv <= maxs_f)))


def _as_1d_float_array(values: Any) -> np.ndarray:
    """Normalize input values to a 1D float NumPy array."""
    v = np.asarray(values, dtype=float)
    if v.ndim == 0:
        return v.reshape(1)
    return v.ravel()


def _iter_devices_and_ranges(devs: DeviceAccess | DeviceAccessList):
    """
    Yield tuples (device, [min, max]) for each underlying device.

    Works for:
      - DeviceAccess: yields 1 item
      - DeviceAccessList: yields N items based on get_devices() and get_range() flattening
    """
    # Single device
    if (
        hasattr(devs, "get")
        and hasattr(devs, "get_range")
        and not hasattr(devs, "get_devices")
    ):
        r = devs.get_range()
        if r is None:
            r = [None, None]
        return [(devs, [r[0], r[1]])]

    # Device list (expects get_devices() + get_range() flat list)
    devices = devs.get_devices()
    flat = np.asarray(devs.get_range(), dtype=object).ravel()
    if (flat.size % 2) != 0:
        raise ValueError(f"dev_range must have an even length, got {flat.size}")

    pairs = []
    for i, d in enumerate(devices):
        pairs.append((d, [flat[2 * i], flat[2 * i + 1]]))
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
        raise ValueError(
            f"Inconsistent sizes: {n} value(s) for {k} device(s). "
            f"Supported: N==K, N==1, or K==1."
        )

    lines = [header]
    for val, (dev, r) in zip(vv, pairs):
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
    Basic control system aggregator for a list of scalar values
    """

    def __init__(self, devs: DeviceAccessList):
        self._devs = devs

    def add_devices(self, devices: DeviceAccess | list[DeviceAccess]):
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


# ------------------------------------------------------------------------------


class CSStrengthScalarAggregator(CSScalarAggregator):
    """
    Control system aggregator for a list of magnet strengths.
    This aggregator is in charge of computing hardware setpoints
    and applying them without overlap.
    When virtual magnets exported from combined function mangets are present (RWMapper),
    the aggregator prevents to apply several times the same power supply setpoint.
    """

    def __init__(self, peer: CSScalarAggregator):
        CSScalarAggregator.__init__(self, peer._devs)
        self.__models: list[MagnetModel] = []  # List of magnet model
        self.__modelToMagnet: list[list[tuple[int, int]]] = []  # strengths indexing
        self.__nbMagnet = 0  # Number of magnet strengths

    def add_magnet(self, magnet: Magnet, devs: list[DeviceAccess]):
        # Incoming magnet can be a magnet exported from
        # a CombinedFunctionMagnet or simple magnet.
        # All magnets exported from a same CombinedFunctionMagnet share the same model
        # TODO: check that strength is supported (m.strength may be None)
        strengthIndex = (
            magnet.strength.index()
            if isinstance(magnet.strength, abstract.RWMapper)
            else 0
        )
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
        allHardwareValues = self._devs.get()  # Read all hardware setpoints
        newHardwareValues = np.zeros(self.nb_device())
        hardwareIndex = 0
        for modelIndex, model in enumerate(self.__models):
            nbDev = len(model.get_devices())
            mStrengths = model.compute_strengths(
                allHardwareValues[hardwareIndex : hardwareIndex + nbDev]
            )
            for valueIdx, strengthIdx in self.__modelToMagnet[modelIndex]:
                mStrengths[strengthIdx] = value[valueIdx]
            newHardwareValues[hardwareIndex : hardwareIndex + nbDev] = (
                model.compute_hardware_values(mStrengths)
            )
            hardwareIndex += nbDev
        dev_range = self._devs.get_range()
        if not check_range(newHardwareValues, dev_range):
            raise PyAMLException(
                format_out_of_range_message(newHardwareValues, self._devs)
            )
        self._devs.set(newHardwareValues)

    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")

    def get(self) -> NDArray[np.float64]:
        allHardwareValues = self._devs.get()  # Read all hardware setpoints
        allStrength = np.zeros(self.__nbMagnet)
        hardwareIndex = 0
        for modelIndex, model in enumerate(self.__models):
            nbDev = len(model.get_devices())
            mStrengths = model.compute_strengths(
                allHardwareValues[hardwareIndex : hardwareIndex + nbDev]
            )
            for valueIdx, strengthIdx in self.__modelToMagnet[modelIndex]:
                allStrength[valueIdx] = mStrengths[strengthIdx]
            hardwareIndex += nbDev
        return allStrength

    def readback(self) -> np.array:
        allHardwareValues = self._devs.readback()  # Read all hardware readback
        allStrength = np.zeros(self.__nbMagnet)
        hardwareIndex = 0
        for modelIndex, model in enumerate(self.__models):
            nbDev = len(model.get_devices())
            mStrengths = model.compute_strengths(
                allHardwareValues[hardwareIndex : hardwareIndex + nbDev]
            )
            for valueIdx, strengthIdx in self.__modelToMagnet[modelIndex]:
                allStrength[valueIdx] = mStrengths[strengthIdx]
            hardwareIndex += nbDev
        return allStrength

    def unit(self) -> str:
        return self._devs.unit()


# ------------------------------------------------------------------------------


class CSBPMArrayMapper(CSScalarAggregator):
    """
    Wrapper to a native CS aggregator for BPM
    """

    def __init__(self, devs: list[DeviceAccess], indices: list[list[int]]):
        self._indices = indices
        self._devs = devs

    def set(self, value: NDArray[np.float64]):
        raise Exception("BPM are not writable")

    def get(self) -> NDArray[np.float64]:
        if len(self._devs) == 1:
            v = self._devs[0].get()
            return v[self._indices[0]]
        else:
            # TODO read using DeviceAccessList
            v0 = self._devs[0].get()[self._indices[0]]
            v1 = self._devs[1].get()[self._indices[1]]
            # Interleave
            xy = np.zeros(v0.size + v1.size)
            xy[0::2] = v0
            xy[1::2] = v1
            return xy

    def readback(self) -> np.array:
        return self.get()

    def unit(self) -> str:
        return self._dev.unit()


# ------------------------------------------------------------------------------


class RWHardwareScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a magnet
    of a control system (in hardware units)
    """

    def __init__(self, model: MagnetModel, dev: DeviceAccess):
        self.__model = model
        self.__dev = dev

    def get(self) -> float:
        return self.__dev.get()

    def set(self, value: float):
        dev_range = self.__dev.get_range()
        if not check_range(value, dev_range):
            raise PyAMLException(format_out_of_range_message(value, self.__dev))
        self.__dev.set(value)

    def set_and_wait(self, value: double):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__model.get_hardware_units()[0]

    def set_magnet_rigidity(self, brho: np.double):
        self.__model.set_magnet_rigidity(brho)


# ------------------------------------------------------------------------------


class RWStrengthScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to a strength of a control system
    """

    def __init__(self, model: MagnetModel, dev: DeviceAccess):
        self.__model = model
        self.__dev = dev

    # Gets the value
    def get(self) -> float:
        current = self.__dev.get()
        return self.__model.compute_strengths([current])[0]

    # Sets the value
    def set(self, value: float):
        current = self.__model.compute_hardware_values([value])[0]
        dev_range = self.__dev.get_range()
        if not check_range(current, dev_range):
            raise PyAMLException(format_out_of_range_message(current, self.__dev))
        self.__dev.set(current)

    # Sets the value and wait that the read value reach the setpoint
    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self.__model.get_strength_units()[0]

    def set_magnet_rigidity(self, brho: np.double):
        self.__model.set_magnet_rigidity(brho)


# ------------------------------------------------------------------------------


class RWHardwareArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a magnet array
    of a control system (in hardware units)
    """

    def __init__(self, model: MagnetModel, devs: list[DeviceAccess]):
        self.__model = model
        self.__devs = devs

    # Gets the value
    def get(self) -> np.array:
        return np.array([p.get() for p in self.__devs])

    # Sets the value
    def set(self, value: np.array):
        for idx, p in enumerate(self.__devs):
            dev_range = p.get_range()
            if not check_range(value[idx], dev_range):
                raise PyAMLException(format_out_of_range_message(value[idx], p))
            p.set(value[idx])

    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_hardware_units()


# ------------------------------------------------------------------------------


class RWStrengthArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to magnet strengths of a control system
    """

    def __init__(self, model: MagnetModel, devs: list[DeviceAccess]):
        self.__model = model
        self.__devs = devs

    # Gets the value
    def get(self) -> np.array:
        r = np.array([p.get() for p in self.__devs])
        str = self.__model.compute_strengths(r)
        return str

    # Sets the value
    def set(self, value: np.array):
        cur = self.__model.compute_hardware_values(value)
        for idx, p in enumerate(self.__devs):
            dev_range = p.get_range()
            if not check_range(cur[idx], dev_range):
                raise PyAMLException(format_out_of_range_message(cur[idx], p))

        for idx, p in enumerate(self.__devs):
            p.set(cur[idx])

    # Sets the value and waits that the read value reach the setpoint
    def set_and_wait(self, value: np.array):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> list[str]:
        return self.__model.get_strength_units()


# ------------------------------------------------------------------------------


class RBpmArray(abstract.ReadFloatArray):
    """
    Class providing read access to a BPM position [x,y] of a control system
    """

    def __init__(self, model: BPMModel, hDev: DeviceAccess, vDev: DeviceAccess):
        self._model = model
        self._hDev = hDev
        self._vDev = vDev
        self._hIdx = self._model.x_pos_index()
        self._vIdx = self._model.y_pos_index()

    # Gets the values
    def get(self) -> np.array:
        if self._hDev != self._vDev:
            allhVal = self._hDev.get()
            allvVal = self._vDev.get()
            hVal = allhVal if self._hIdx is None else allhVal[self._hIdx]
            vVal = allvVal if self._vIdx is None else allvVal[self._vIdx]
        else:
            # When h and v devices are identical, indexed
            # values are expected
            allVal = self._hDev.get()
            hVal = allVal[self._hIdx]
            vVal = allVal[self._vIdx]
        return np.array([hVal, vVal])

    # Gets the unit of the value Assume that x and y, offsets and positions
    # have the same unit
    def unit(self) -> str:
        return self._model.get_pos_devices()[0].unit()


# ------------------------------------------------------------------------------


class RWBpmTiltScalar(abstract.ReadFloatScalar):
    """
    Class providing read access to a BPM tilt of a control system
    """

    def __init__(self, model: BPMModel, dev: DeviceAccess):
        self._model = model
        self._dev = dev
        self._idx = model.tilt_index()

    # Gets the value
    def get(self) -> float:
        allTilt = self._dev.get()
        if self._idx is not None:
            return allTilt[self._idx]
        else:
            return allTilt

    def set(self, value: float):
        self._dev.set(value)

    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value
    def unit(self) -> str:
        return self._model.get_tilt_device().unit()


# ------------------------------------------------------------------------------


class RWBpmOffsetArray(abstract.ReadWriteFloatArray):
    """
    Class providing read write access to a BPM offset [x,y] of a control system
    """

    def __init__(self, model: BPMModel, hDev: DeviceAccess, vDev: DeviceAccess):
        self._model = model
        self._hDev = hDev
        self._vDev = vDev
        self._hIdx = self._model.x_pos_index()
        self._vIdx = self._model.y_pos_index()

    # Gets the values
    def get(self) -> np.array:
        if self._hDev != self._vDev:
            allhVal = self._hDev.get()
            allvVal = self._vDev.get()
            hVal = allhVal if self._hIdx is None else allhVal[self._hIdx]
            vVal = allvVal if self._vIdx is None else allvVal[self._vIdx]
        else:
            # When h and v devices are identical, indexed
            # values are expected
            allVal = self._hDev.get()
            hVal = allVal[self._hIdx]
            vVal = allVal[self._vIdx]
        return np.array([hVal, vVal])

    # Sets the values
    def set(self, value: NDArray[np.float64]):
        if self._hDev != self._vDev:
            self._hDev.set(value[0])
            self._vDev.set(value[1])
        else:
            # When h and v devices are identical, indexed
            # values are expected
            newValue = self._hDev.get()
            newValue[self._hIdx] = value[0]
            newValue[self._vIdx] = value[1]
            self._hDev.set(newValue)

    def set_and_wait(self, value: NDArray[np.float64]):
        raise NotImplementedError("Not implemented yet.")

    # Gets the unit of the value Assume that x and y, offsets and positions
    # have the same unit
    def unit(self) -> str:
        return self._model.get_pos_devices()[0].unit()


# ------------------------------------------------------------------------------


class RWRFVoltageScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity voltage
    for a transmitter of a control system.
    """

    def __init__(self, transmitter: RFTransmitter, dev: DeviceAccess):
        self.__transmitter = transmitter
        self.__dev = dev

    def get(self) -> float:
        return self.__dev.get()

    def set(self, value: float):
        self.__dev.set(value)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__transmitter._cfg.voltage.unit()


# ------------------------------------------------------------------------------


class RWRFPhaseScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to cavity phase
    for a transmitter of a control system.
    """

    def __init__(self, transmitter: RFTransmitter, dev: DeviceAccess):
        self.__transmitter = transmitter
        self.__dev = dev

    def get(self) -> float:
        return self.__dev.get()

    def set(self, value: float):
        self.__dev.set(value)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__transmitter._cfg.phase.unit()


# ------------------------------------------------------------------------------


class RWRFFrequencyScalar(abstract.ReadWriteFloatScalar):
    """
    Class providing read write access to RF frequency of a control system.
    """

    def __init__(self, rf: RFPlant, dev: DeviceAccess):
        self.__rf = rf
        self.__dev = dev

    def get(self) -> float:
        # Serialized cavity has the same frequency
        return self.__dev.get()

    def set(self, value: float):
        self.__dev.set(value)

    def set_and_wait(self, value: float):
        raise NotImplementedError("Not implemented yet.")

    def unit(self) -> str:
        return self.__rf._cfg.masterclock.unit()


# ------------------------------------------------------------------------------


class RBetatronTuneArray(abstract.ReadFloatArray):
    """
    Class providing read write access to betatron tune of a control system.
    """

    def __init__(self, tune_monitor, devs: list[DeviceAccess]):
        self.__tune_monitor = tune_monitor
        self.__devs = devs

    def get(self) -> NDArray:
        # Return horizontal and vertical betatron tunes as a NumPy array
        return np.array(
            [
                self.__devs[0].get(),
                self.__devs[1].get(),
            ]
        )

    def unit(self) -> str:
        return self.__tune_monitor._cfg.tune_v.unit()


# ------------------------------------------------------------------------------


class RChromaticityArray(abstract.ReadFloatArray):
    """
    Class providing read write access to chromaticity of a control system.
    """

    def __init__(self, chromaticity_monitor):
        self.__chromaticity_monitor = chromaticity_monitor

    def _update_chromaticity_monitor(self, chromaticity_monitor):
        """Use to attach the proper chromaticity_monitor and not the one used to create this instance"""
        self.__chromaticity_monitor = chromaticity_monitor

    def get(self) -> NDArray:
        # Return horizontal and vertical chromaticity as a NumPy array
        return self.__chromaticity_monitor._last_measured

    def unit(self) -> str:
        return "1"
