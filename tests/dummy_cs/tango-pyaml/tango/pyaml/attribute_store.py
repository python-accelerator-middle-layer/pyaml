from dataclasses import dataclass
from typing import Any


@dataclass
class AttributeState:
    """Shared mutable state for one dummy Tango attribute."""

    value: Any = 0.0
    unit: str = ""
    range: tuple[float | None, float | None] | None = None
    readback: Any = None
    is_array: bool = False


_ATTRIBUTES: dict[str, AttributeState] = {}
"""Registry keyed by Tango attribute name.

Tests generally initialize attributes with their configuration name
(`srdiag/bpm/...`). The dummy control system later prefixes the attribute with
the Tango host (`//host/srdiag/bpm/...`). Both names must resolve to the same
state so initialization done before `Accelerator.load()` remains visible after
control-system attachment.
"""


def _unqualified_name(name: str) -> str:
    """Strip the optional Tango host prefix from `//host/device/attribute`."""
    if name.startswith("//"):
        parts = name.split("/", 3)
        if len(parts) == 4:
            return parts[3]
    return name


def _lookup_existing_state(name: str) -> AttributeState | None:
    """Find an existing state using either full or host-less attribute name."""
    state = _ATTRIBUTES.get(name)
    if state is not None:
        return state

    unqualified = _unqualified_name(name)
    if unqualified != name:
        state = _ATTRIBUTES.get(unqualified)
        if state is not None:
            # Alias the full Tango name to the pre-loaded host-less state.
            _ATTRIBUTES[name] = state
            return state

    return None


def get_state(
    name: str,
    *,
    unit: str = "",
    range: tuple[float | None, float | None] | None = None,
) -> AttributeState:
    """Return the shared state for an attribute, creating it if necessary."""
    state = _lookup_existing_state(name)
    if state is None:
        state = AttributeState(unit=unit, range=range)
        _ATTRIBUTES[name] = state
    else:
        if unit and not state.unit:
            state.unit = unit
        if range is not None and state.range is None:
            state.range = range

    return state


def set_attribute(
    name: str,
    value: Any,
    *,
    unit: str = "",
    range: tuple[float | None, float | None] | None = None,
    readback: Any = None,
) -> AttributeState:
    """Set or initialize a dummy Tango attribute value from a test."""
    state = _lookup_existing_state(name)
    if state is None:
        state = AttributeState()

    state.value = value
    state.readback = readback
    state.is_array = _is_array_value(value)
    if unit:
        state.unit = unit
    if range is not None:
        state.range = range

    _ATTRIBUTES[name] = state
    return state


def get_attribute(name: str) -> Any:
    """Return the current value stored for a dummy Tango attribute."""
    return get_state(name).value


def clear_attributes():
    """Clear all dummy Tango values to avoid state leakage between tests."""
    _ATTRIBUTES.clear()


def _is_array_value(value: Any) -> bool:
    """Return true for vector-like values, but keep strings scalar."""
    if isinstance(value, (str, bytes)):
        return False
    try:
        len(value)
    except TypeError:
        return False
    return True
