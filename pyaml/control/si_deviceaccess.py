"""
SI unit conversion of control-system devices.

Backends expose device values in the unit of the control system (``nm``,
``MHz``, ``mA``...). PyAML works in SI. The wrappers of this module sit between
the backend :class:`~pyaml.control.deviceaccess.DeviceAccess` /
:class:`~pyaml.control.deviceaccesslist.DeviceAccessList` and the PyAML
accessors, and apply the multiplicative factor computed once with pint by
:func:`pyaml.common.units.conversion_factor`.

The target unit is fixed by the PyAML accessor (``m`` for BPM positions,
``Hz`` for the RF frequency, the model hardware unit for a magnet...), not by
the backend, so that live and design modes return the same quantities.
"""

from typing import Any

import numpy as np
import numpy.typing as npt

from ..common.exception import PyAMLConfigException
from ..common.units import conversion_factor
from .deviceaccess import DeviceAccess
from .deviceaccesslist import DeviceAccessList
from .readback_value import Value


def _scale(value: Any, k: float | np.ndarray, inverse: bool = False) -> Any:
    """
    Multiply a raw device value by ``k`` (one factor, or one per element), or divide it when ``inverse``.

    Handles scalars, numeric arrays, :class:`Value` objects (metadata kept) and
    lists/object arrays of them, as returned by ``readback()``.
    """
    if value is None:
        return None
    if isinstance(value, Value):
        return Value(_scale(value.value, k, inverse), value.quality, value.timestamp)
    if isinstance(value, (list, tuple)) or (isinstance(value, np.ndarray) and value.dtype == object):
        ks = np.broadcast_to(k, (len(value),))
        scaled = [_scale(v, kk, inverse) for v, kk in zip(value, ks, strict=True)]
        return np.array(scaled, dtype=object) if isinstance(value, np.ndarray) else scaled
    return value / k if inverse else value * k


def _scale_range(rng: list | None, k: float | np.ndarray) -> list | None:
    """Scale a flat ``[min0, max0, min1, max1, ...]`` range, keeping ``None`` bounds (factors are positive)."""
    if rng is None:
        return None
    ks = np.repeat(np.broadcast_to(k, (len(rng) // 2,)), 2)
    return [None if b is None else b * kk for b, kk in zip(rng, ks, strict=True)]


class SIDeviceAccess(DeviceAccess):
    """
    Expose a backend device in the SI unit expected by PyAML.

    Parameters
    ----------
    raw : DeviceAccess
        Backend device, read and written in its own unit (``raw.unit()``).
    si_unit : str
        Unit in which values are exposed to PyAML.

    Attributes
    ----------
    raw : DeviceAccess
        The wrapped backend device.
    factor : float
        Conversion factor, ``si_value = factor * raw_value``.

    Methods
    -------
    name()
        Return the backend identifier of the device variable.
    measure_name()
        Return the identifier of the device's measurement channel.
    set(value)
        Convert a SI setpoint to the device unit and write it.
    set_and_wait(value)
        Convert a SI setpoint to the device unit, write it and wait.
    get()
        Return the current setpoint in SI.
    readback()
        Return the latest measured value in SI.
    unit()
        Return the pyAML unit for this quantity, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit of the wrapped backend device.
    get_range()
        Return the device range in SI.
    check_device_availability()
        Check if the device is available and accessible.
    """

    def __init__(self, raw: DeviceAccess, si_unit: str, factor: float = 1.0):
        self.raw = raw
        self.factor = factor
        self._si_unit = si_unit

    def name(self) -> str:
        """Return the backend identifier of the device variable."""
        return self.raw.name()

    def measure_name(self) -> str:
        """Return the identifier of the device's measurement channel."""
        return self.raw.measure_name()

    def set(self, value):
        """Convert a SI setpoint to the device unit and write it."""
        self.raw.set(value if self.factor == 1.0 else _scale(value, self.factor, inverse=True))

    def set_and_wait(self, value):
        """Convert a SI setpoint to the device unit, write it and wait."""
        self.raw.set_and_wait(value if self.factor == 1.0 else _scale(value, self.factor, inverse=True))

    def get(self):
        """Return the current setpoint in SI."""
        v = self.raw.get()
        return v if self.factor == 1.0 else _scale(v, self.factor)

    def readback(self):
        """Return the latest measured value in SI."""
        v = self.raw.readback()
        return v if self.factor == 1.0 else _scale(v, self.factor)

    def unit(self) -> str:
        """Return the pyAML unit for this quantity, i.e. returned by get() and expected by set()."""
        return self._si_unit

    def control_system_unit(self) -> str | None:
        """Return the control-system unit of the wrapped backend device."""
        return self.raw.unit()

    def get_range(self) -> list[float]:
        """Return the device range in SI."""
        rng = self.raw.get_range()
        return rng if self.factor == 1.0 else _scale_range(rng, self.factor)

    def check_device_availability(self) -> bool:
        """Check if the device is available and accessible."""
        return self.raw.check_device_availability()

    def __str__(self):
        return str(self.raw)

    def __repr__(self):
        return f"SIDeviceAccess({self.raw!r}, si_unit='{self._si_unit}', factor={self.factor:g})"


def wrap_si(dev: DeviceAccess | None, si_unit: str | None) -> DeviceAccess | None:
    """
    Wrap ``dev`` so that it is read and written in ``si_unit``.

    Parameters
    ----------
    dev : DeviceAccess or None
        Backend device. ``None`` is returned unchanged (missing device).
    si_unit : str or None
        Unit expected by the PyAML accessor.

    Returns
    -------
    DeviceAccess or None
        A :class:`SIDeviceAccess` (with factor 1 when no conversion is
        needed), or ``dev`` itself when ``si_unit`` is empty or ``None``.

    Raises
    ------
    PyAMLConfigException
        If the device unit cannot be converted to ``si_unit``.
    """
    if dev is None or isinstance(dev, SIDeviceAccess) or si_unit is None or not str(si_unit).strip():
        return dev
    try:
        k = conversion_factor(dev.unit(), si_unit)
    except PyAMLConfigException as e:
        raise PyAMLConfigException(f"Device '{dev.name()}': {e}") from e
    return SIDeviceAccess(dev, si_unit, k)


class SIDeviceAccessList(DeviceAccessList):
    """
    Expose a backend device list in the SI units expected by PyAML.

    The backend list only receives raw backend devices (it may need them to
    perform grouped reads); the conversion factor of each device is kept here.

    Parameters
    ----------
    raw : DeviceAccessList
        Backend device list.

    Attributes
    ----------
    raw : DeviceAccessList
        The wrapped backend device list.
    factors : numpy.ndarray
        Conversion factors, one per device (``si_value = factor * raw_value``).

    Methods
    -------
    add_devices(devices)
        Add raw or SI-wrapped devices.
    get_device_at(index)
        Return the (SI-wrapped) device at ``index``.
    len()
        Return the number of devices.
    set(value)
        Convert SI setpoints to device units and write them.
    set_and_wait(value)
        Convert SI setpoints to device units, write them and wait.
    get()
        Return all setpoints in SI.
    readback()
        Return all readbacks in SI.
    unit()
        Return the pyAML unit for each device, i.e. returned by get() and expected by set().
    control_system_unit()
        Return the control-system unit of each wrapped backend device.
    get_range()
        Return the ranges in SI.
    check_device_availability()
        Check if all devices are available.
    """

    def __init__(self, raw: DeviceAccessList):
        self.raw = raw
        self._items: list[DeviceAccess] = []
        self.factors = np.ones(0)  # Conversion factors, one per device
        self._passthrough = True  # True while all factors are 1

    def add_devices(self, devices: DeviceAccess | list[DeviceAccess]):
        """Add raw or SI-wrapped devices."""
        devs = devices if isinstance(devices, list) else [devices]
        raws = [d.raw if isinstance(d, SIDeviceAccess) else d for d in devs]
        self.raw.add_devices(raws if isinstance(devices, list) else raws[0])
        self._items.extend(devs)
        k = [d.factor if isinstance(d, SIDeviceAccess) else 1.0 for d in devs]
        self.factors = np.concatenate([self.factors, k])
        self._passthrough = bool(np.all(self.factors == 1.0))

    def get_device_at(self, index: int) -> DeviceAccess:
        """Return the (SI-wrapped) device at ``index``."""
        return self._items[index]

    def len(self) -> int:
        """Return the number of devices."""
        return len(self._items)

    def set(self, value: npt.NDArray[np.float64]):
        """Convert SI setpoints to device units and write them."""
        self.raw.set(value if self._passthrough else np.asarray(value, dtype=float) / self.factors)

    def set_and_wait(self, value: npt.NDArray[np.float64]):
        """Convert SI setpoints to device units, write them and wait."""
        self.raw.set_and_wait(value if self._passthrough else np.asarray(value, dtype=float) / self.factors)

    def get(self) -> npt.NDArray[np.float64]:
        """Return all setpoints in SI."""
        v = self.raw.get()
        return v if self._passthrough else np.asarray(v, dtype=float) * self.factors

    def readback(self) -> np.array:
        """Return all readbacks in SI."""
        v = self.raw.readback()
        return v if self._passthrough or v is None or len(v) == 0 else _scale(v, self.factors)

    def unit(self) -> list[str]:
        """Return the pyAML unit for each device, i.e. returned by get() and expected by set()."""
        return [d.unit() for d in self._items]

    def control_system_unit(self) -> list[str | None]:
        """Return the control-system unit of each wrapped backend device."""
        return [control_system_unit_of(d) for d in self._items]

    def get_range(self) -> list[float]:
        """Return the ranges in SI."""
        rng = self.raw.get_range()
        return rng if self._passthrough else _scale_range(rng, self.factors)

    def check_device_availability(self) -> bool:
        """Check if all devices are available."""
        return self.raw.check_device_availability()


def control_system_unit_of(dev: DeviceAccess | None) -> str | None:
    """
    Return the control-system unit of ``dev``.

    Parameters
    ----------
    dev : DeviceAccess or None
        Backend device, possibly wrapped in a :class:`SIDeviceAccess`.

    Returns
    -------
    str or None
        Unit reported by the backend device, ``None`` for a missing device.
    """
    if dev is None:
        return None
    return dev.control_system_unit() if isinstance(dev, SIDeviceAccess) else dev.unit()
