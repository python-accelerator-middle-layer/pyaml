"""Backend-neutral live insertion-device accessors."""

import time

from ..common.abstract import ReadFloatScalar, ReadWriteFloatScalar
from ..common.exception import PyAMLConfigException, PyAMLException
from .abstract_impl import RWScalarBoolean, check_range, format_out_of_range_message
from .deviceaccess import DeviceAccess
from .readback_value import Value


class InsertionDeviceMode:
    """Expose an optional mode; the control system owns allowed transitions."""

    def __init__(self, device: DeviceAccess):
        self._device = device

    def get(self) -> str:
        value = self._device.readback()
        if isinstance(value, Value):
            value = value.value
        if not isinstance(value, str) or not value.strip():
            raise PyAMLException(f"{self._device.name()}: expected a nonempty string mode, got {value!r}")
        return value

    def set(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise PyAMLException(f"{self._device.name()}: expected a nonempty string mode, got {value!r}")
        self._device.set(value)


class RInsertionDeviceControlVariable(ReadFloatScalar):
    """Read an ID control variable, its setpoint, units and backend limits."""

    def __init__(self, device: DeviceAccess, unit: str, moving: RWScalarBoolean | None = None):
        if device.unit() != unit:
            raise PyAMLConfigException(
                f"{device.name()}: backend unit {device.unit()!r} does not match configured unit {unit!r}"
            )
        self._device = device
        self._unit = unit
        self.moving = moving

    def get(self) -> float:
        return float(self._device.readback())

    def get_setpoint(self) -> float:
        return float(self._device.get())

    def unit(self) -> str:
        return self._unit

    def get_range(self) -> list[float | None]:
        return self._device.get_range()


class RWInsertionDeviceControlVariable(RInsertionDeviceControlVariable, ReadWriteFloatScalar):
    """Write a control variable, optionally waiting on its boolean movement flag."""

    def set(self, value: float) -> None:
        if not check_range(value, self.get_range()):
            raise PyAMLException(format_out_of_range_message(value, self._device))
        self._device.set(value)

    def set_and_wait(self, value: float) -> None:
        if self.moving is None:
            raise PyAMLException(
                f"{self._device.name()}: set_and_wait requires a movement_flag; use set() for current variables"
            )
        self.set(value)
        while self.moving.get():
            time.sleep(0.1)
