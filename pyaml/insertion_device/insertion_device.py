"""Insertion-device holding class, independent of facility control systems.

Example (the lattice already contains the kickmap)::

    - type: pyaml.insertion_device
      name: APPLE01
      device_id: APPLE01_SERIAL
      lattice_names: ID02
      description: Kickmap measured at 4 mm gap and zero phase.
      control_variables:
        gap: {unit: mm, backend: APPLE01_GAP, movement_flag: APPLE01_GAP_MOVING}
        phase: {unit: mm, backend: APPLE01_PHASE, movement_flag: APPLE01_MOVING}
      control_mode: APPLE01_MODE
      model_operating_point: {gap: 4.0, phase: 0.0, mode: parallel}
      orbit_feedforward: ID01_ORBIT_FF

Runtime ``control_variables`` use existing pyAML scalar accessors. An absent key
means no configured variable; None means configured but unavailable.
Both backends expose ReadWriteFloatScalar accessors; the fixed model rejects
control-variable writes.

Live control variables bind through opaque backend references. ``get()`` reads
the requested setpoint; ``readback()`` reads the measured value. Without a backend
reference a variable remains unavailable. Gap and phase/shift variables use
``set_and_wait()`` with a configured boolean movement flag. PS1 and other current
controls have no movement flags and use plain ``set()``. Sequencing and interlocks
remain control-system concerns.
FFWD objects own their correctors, controls and measurements.

The same class supports phase-only devices (including a fixed gap in the model
reference) and electromagnetic devices with arbitrarily named current variables::

    - type: pyaml.insertion_device
      name: EM01
      device_id: EM01_SERIAL
      lattice_names: ID03
      control_variables:
        ps1: {unit: A, backend: EM01_PS1}
        ps2: {unit: A, backend: EM01_PS2}
        ps3: {unit: A, backend: EM01_PS3}
      model_operating_point: {ps1: 100.0, ps2: 0.0, ps3: 0.0}

After retrieving a device through ``sr.live.insertion_device.get(name)``, use
``device.control_variables["gap"].set_and_wait(12.0)`` for gap or phase/shift
motion, or ``device.control_variables["ps1"].set(100.0)`` for a current control
without a movement flag. For gap and phase/shift motion, waiting only polls the
boolean flag until false: no readback tolerance, moving edge detection, or
timeout policy is added. Without a movement flag, ``set_and_wait()`` raises
before writing. Backend errors propagate unchanged.
Optional controls use ``device.mode.get()/set(value)`` and
``device.flags[name].get()/set(value)``; the latter reuse ``RWScalarBoolean``.

In a simulator, variable reads report the configured reference point and all
control-variable writes raise an error. ``device.model.disable()`` delegates to pyAT's
same-length drift/identity approximation; ``enable()`` restores the kickmap.
Neither operation changes the reference point or any hardware.
"""

import copy
import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Self

from ..common.abstract import ReadWriteFloatScalar
from ..common.element import Element
from ..common.exception import PyAMLConfigException
from ..validation import DynamicValidation, register_schema

if TYPE_CHECKING:
    from ..common.holders.element_holder import ElementHolder
    from ..control.abstract_impl import RWScalarBoolean
    from ..control.insertion_device import RWInsertionDeviceMode
    from ..lattice import insertion_device

PYAMLCLASS = "InsertionDevice"


@register_schema
class InsertionDevice(Element, DynamicValidation):
    """Hold control variables and references to other pyAML elements.

    ``control_variables`` configures units and opaque backend references.
    Live control variables are always read/write. Gap and phase/shift variables may
    configure a ``movement_flag`` for ``set_and_wait()``. Current controls have
    no movement flags and use ``set()``.
    After attachment, the same attribute exposes the bound scalar accessors.
    At least one named variable is required, but no particular gap, phase or
    current channel is mandatory.
    ``model_operating_point`` is flat: numeric coordinates and optional string
    ``mode``. Missing coordinates never imply zero. Additional provenance may
    be recorded in the free-form ``description``.

    ``control_mode`` and boolean ``flags`` are opaque backend references.
    ``orbit_feedforward`` and ``tune_feedforward`` reference existing elements
    in the same holder, resolved after attachment. Runtime ``mode`` and ``flags``
    expose the optional backend controls.
    """

    def __init__(
        self,
        name: str,
        device_id: str,
        control_variables: dict[str, dict[str, str]] | None = None,
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
        if not control_variables:
            raise PyAMLConfigException(f"{name}: at least one control variable is required")
        for key, definition in control_variables.items():
            if not key.strip() or not definition.get("unit", "").strip():
                raise PyAMLConfigException(f"{name}: each control variable requires a name and unit")
            if set(definition) - {"unit", "backend", "movement_flag"}:
                raise PyAMLConfigException(f"{name}.{key}: expected only unit, backend and movement_flag")
            for field in ("backend", "movement_flag"):
                if field in definition and not definition[field].strip():
                    raise PyAMLConfigException(f"{name}.{key}: {field} must not be empty")
        if any(not key.strip() or not value.strip() for key, value in (flags or {}).items()):
            raise PyAMLConfigException(f"{name}: flag names and references must not be empty")
        if control_mode is not None and not control_mode.strip():
            raise PyAMLConfigException(f"{name}: control_mode must not be empty")
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
        self._control_variable_definitions = copy.deepcopy(control_variables)
        self._flag_refs = dict(flags or {})
        self._point = dict(model_operating_point) if model_operating_point is not None else None
        self._control_variables: dict[str, ReadWriteFloatScalar | None] = dict.fromkeys(self._control_variable_definitions)
        self._flags: dict[str, RWScalarBoolean | None] = dict.fromkeys(self._flag_refs)
        self.mode: RWInsertionDeviceMode | None = None
        self.orbit_feedforward: Element | None = None
        self.tune_feedforward: Element | None = None
        self.model: insertion_device.InsertionDevice | None = None

    @property
    def control_variables(self) -> Mapping[str, ReadWriteFloatScalar | None]:
        """Bound scalar accessors, or None for configured but unavailable variables."""
        return MappingProxyType(self._control_variables)

    @property
    def flags(self) -> Mapping[str, "RWScalarBoolean | None"]:
        """Boolean backend controls, or None when unavailable in this holder."""
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
        control_variables: Mapping[str, ReadWriteFloatScalar | None] | None = None,
        model: "insertion_device.InsertionDevice | None" = None,
        flags: Mapping[str, "RWScalarBoolean | None"] | None = None,
        mode: "RWInsertionDeviceMode | None" = None,
    ) -> Self:
        """Return a per-peer copy; defaults give metadata-only access."""
        obj = copy.copy(self)
        obj._peer = peer
        obj._control_variables = (
            dict(control_variables) if control_variables is not None else dict.fromkeys(self._control_variable_definitions)
        )
        obj._flags = dict(flags) if flags is not None else dict.fromkeys(self._flag_refs)
        obj.mode = mode
        obj.orbit_feedforward = obj.tune_feedforward = None
        obj.model = model
        return obj

    def _fill_device(self, holder: "ElementHolder") -> None:
        holder._fill_insertion_device(self)

    def post_init(self) -> None:
        self.check_peer()
        self.orbit_feedforward = self.peer[self.orbit_feedforward_name] if self.orbit_feedforward_name is not None else None
        self.tune_feedforward = self.peer[self.tune_feedforward_name] if self.tune_feedforward_name is not None else None
