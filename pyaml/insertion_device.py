"""Insertion-device holding class, independent of facility control systems.

Example (the lattice already contains the kickmap)::

    - type: pyaml.insertion_device
      name: APPLE01
      device_id: APPLE01_SERIAL
      lattice_names: ID02
      description: Kickmap measured at 4 mm gap and zero phase.
      drives:
        gap: {unit: mm, backend: APPLE01_GAP}
        phase: {unit: mm, backend: APPLE01_PHASE, movement_flag: APPLE01_MOVING}
      control_mode: APPLE01_MODE
      model_operating_point: {gap: 4.0, phase: 0.0, mode: parallel}
      orbit_feedforward: ID01_ORBIT_FF

Runtime ``components`` use existing pyAML scalar accessors. An absent key means
no configured drive; None means configured but unavailable. ReadFloatScalar
and ReadWriteFloatScalar distinguish read-only and writable drives.

Live attachment initially exposes metadata only, never simulated hardware
readings. Facility adapters own motion and errors: gap/phase adapters use the
boolean movement flag; electromagnetic adapters initially use plain set().
FFWD objects own their correctors, controls and measurements.

In a simulator, drive reads report the configured reference point; writes accept
only that exact value as a no-op. ``device.model.disable()`` delegates to pyAT's
same-length drift/identity approximation; ``enable()`` restores the kickmap.
Neither operation changes the reference point or any hardware.
"""

import copy
import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Self

from .common.abstract import ReadFloatScalar
from .common.element import Element
from .common.exception import PyAMLConfigException
from .validation import DynamicValidation, register_schema

if TYPE_CHECKING:
    from .common.holders.element_holder import ElementHolder
    from .lattice.insertion_device import FixedInsertionDeviceModel

PYAMLCLASS = "InsertionDevice"


@register_schema
class InsertionDevice(Element, DynamicValidation):
    """Hold optional drives and references to other pyAML elements.

    ``drives`` accepts unit, opaque backend reference and optional movement_flag.
    No gap, phase or current channel is mandatory in this shared class.
    ``model_operating_point`` is flat: numeric coordinates and optional string
    ``mode``. Missing coordinates never imply zero. Additional provenance may
    be recorded in the free-form ``description``.

    ``control_mode`` and boolean ``flags`` are opaque backend references.
    ``orbit_feedforward`` and ``tune_feedforward`` reference existing elements
    in the same holder, resolved after attachment.
    """

    def __init__(
        self,
        name: str,
        device_id: str,
        drives: dict[str, dict[str, str]] | None = None,
        control_mode: str | None = None,
        flags: dict[str, str] | None = None,
        orbit_feedforward: str | None = None,
        tune_feedforward: str | None = None,
        model_operating_point: dict[str, float | str] | None = None,
        lattice_names: str | None = None,
        description: str | None = None,
    ):
        super().__init__(name, lattice_names, description)
        if not device_id.strip():
            raise PyAMLConfigException(f"{name}: device_id must not be empty")
        for key, definition in (drives or {}).items():
            if not key.strip() or not definition.get("unit", "").strip():
                raise PyAMLConfigException(f"{name}: each drive requires a name and unit")
            if set(definition) - {"unit", "backend", "movement_flag"}:
                raise PyAMLConfigException(f"{name}.{key}: expected only unit, backend and movement_flag")
        for key, value in (model_operating_point or {}).items():
            valid = (
                isinstance(value, str) and bool(value.strip())
                if key == "mode"
                else (isinstance(value, (int, float)) and math.isfinite(value))
            )
            if not key.strip() or not valid:
                raise PyAMLConfigException(f"{name}.{key}: expected a finite coordinate or string mode")
        self.device_id = device_id
        self.control_mode = control_mode
        self.orbit_feedforward_name = orbit_feedforward
        self.tune_feedforward_name = tune_feedforward
        self._drives = copy.deepcopy(drives or {})
        self._flag_refs = dict(flags or {})
        self._point = dict(model_operating_point) if model_operating_point is not None else None
        self._components: dict[str, ReadFloatScalar | None] = dict.fromkeys(self._drives)
        self._flags: dict[str, None] = dict.fromkeys(self._flag_refs)
        self.orbit_feedforward: Element | None = None
        self.tune_feedforward: Element | None = None
        self.model: FixedInsertionDeviceModel | None = None

    @property
    def drives(self) -> dict[str, dict[str, str]]:
        """Return drive configuration, not runtime values."""
        return copy.deepcopy(self._drives)

    @property
    def components(self) -> Mapping[str, ReadFloatScalar | None]:
        return MappingProxyType(self._components)

    @property
    def flags(self) -> Mapping[str, None]:
        """Configured boolean flags; runtime binding is deferred to adapters."""
        return MappingProxyType(self._flags)

    @property
    def flag_references(self) -> Mapping[str, str]:
        return MappingProxyType(self._flag_refs)

    @property
    def model_operating_point(self) -> Mapping[str, float | str] | None:
        return MappingProxyType(self._point) if self._point is not None else None

    def attach(
        self,
        peer: "ElementHolder",
        components: Mapping[str, ReadFloatScalar | None] | None = None,
        model: "FixedInsertionDeviceModel | None" = None,
    ) -> Self:
        """Return a per-peer copy; defaults give metadata-only access."""
        obj = copy.copy(self)
        obj._peer = peer
        obj._components = dict(components) if components is not None else dict.fromkeys(self._drives)
        obj._flags = dict.fromkeys(self._flag_refs)
        obj.orbit_feedforward = obj.tune_feedforward = None
        obj.model = model
        return obj

    def _fill_device(self, holder: "ElementHolder") -> None:
        holder._fill_insertion_device(self)

    def post_init(self) -> None:
        self.check_peer()
        self.orbit_feedforward = self.peer[self.orbit_feedforward_name] if self.orbit_feedforward_name is not None else None
        self.tune_feedforward = self.peer[self.tune_feedforward_name] if self.tune_feedforward_name is not None else None
