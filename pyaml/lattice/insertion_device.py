"""Fixed-operating-point insertion-device accessors for pyAT."""

import copy
import math
from typing import TYPE_CHECKING

import at

from ..common.abstract import ReadFloatScalar
from ..common.exception import PyAMLException
from ..insertion_device import InsertionDevice

if TYPE_CHECKING:
    from ..common.holders.element_holder import ElementHolder


class _FixedDrive(ReadFloatScalar):
    def __init__(self, name: str, value: float, unit: str):
        self._name = name
        self._value = value
        self._unit = unit

    def get(self) -> float:
        return self._value

    def get_setpoint(self) -> float:
        """Return the model reference, not a hardware setpoint."""
        return self._value

    def unit(self) -> str:
        return self._unit

    def set(self, value: float) -> None:
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value != self._value:
            raise PyAMLException(f"{self._name}: fixed model operating point does not support {value!r}")

    def set_and_wait(self, value: float) -> None:
        self.set(value)


class FixedInsertionDeviceModel:
    """Linked kickmap segment(s) and their fixed reference, independent of hardware."""

    def __init__(self, device: InsertionDevice, kickmaps: list[at.InsertionDeviceKickMap]):
        point = device.model_operating_point
        if point is None or not set(device.drives).issubset(point):
            raise PyAMLException(f"{device.name}: model_operating_point must include every configured drive")
        if device.control_mode is not None and "mode" not in point:
            raise PyAMLException(f"{device.name}: model_operating_point must include mode")
        self._name = device.name
        self._point = dict(point)
        self._kickmaps = tuple(kickmaps)
        self._reference = {
            "device_id": device.device_id,
            "description": device.description,
            "operating_point": dict(point),
            "units": {name: definition["unit"] for name, definition in device.drives.items()},
            "maps": tuple(getattr(element, "Filename_in", None) for element in kickmaps),
        }

    @property
    def reference(self) -> dict:
        """Return reference coordinates/provenance, never live hardware values."""
        return copy.deepcopy(self._reference)

    @property
    def mode(self) -> str | None:
        value = self._point.get("mode")
        return value if isinstance(value, str) else None

    @mode.setter
    def mode(self, value: str) -> None:
        if self.mode is None or value != self.mode:
            raise PyAMLException(f"{self._name}: fixed model operating point does not support mode {value!r}")

    @property
    def enabled(self) -> bool:
        states = {element.PassMethod not in ("DriftPass", "IdentityPass") for element in self._kickmaps}
        if len(states) != 1:
            raise PyAMLException(f"{self._name}: inconsistent kickmap enabled states")
        return states.pop()

    def enable(self) -> None:
        """Restore kickmap tracking through pyAT, without changing its reference."""
        for element in self._kickmaps:
            element.enable()

    def disable(self) -> None:
        """Use pyAT's same-length drift/identity approximation, not hardware motion."""
        for element in self._kickmaps:
            element.disable()

    def attach(self, device: InsertionDevice, peer: "ElementHolder") -> InsertionDevice:
        components = {}
        for name, definition in device.drives.items():
            value = self._point[name]
            if not isinstance(value, (int, float)):
                raise PyAMLException(f"{device.name}.{name}: numeric model reference is required")
            components[name] = _FixedDrive(f"{device.name}.{name}", float(value), definition["unit"])
        return device.attach(peer, components, self)
