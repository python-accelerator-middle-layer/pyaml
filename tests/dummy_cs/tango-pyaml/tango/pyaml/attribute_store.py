from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass
class AttributeState:
    value: Any = 0.0
    unit: str = ""
    range: Optional[Tuple[Optional[float], Optional[float]]] = None
    readback: Any = None
    is_array: bool = False


_ATTRIBUTES: dict[str, AttributeState] = {}


def _unqualified_name(name: str) -> str:
    if name.startswith("//"):
        parts = name.split("/", 3)
        if len(parts) == 4:
            return parts[3]
    return name


def _lookup_existing_state(name: str) -> AttributeState | None:
    state = _ATTRIBUTES.get(name)
    if state is not None:
        return state

    unqualified = _unqualified_name(name)
    if unqualified != name:
        state = _ATTRIBUTES.get(unqualified)
        if state is not None:
            _ATTRIBUTES[name] = state
            return state

    return None


def get_state(
    name: str,
    *,
    unit: str = "",
    range: Optional[Tuple[Optional[float], Optional[float]]] = None,
) -> AttributeState:
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
    range: Optional[Tuple[Optional[float], Optional[float]]] = None,
    readback: Any = None,
) -> AttributeState:
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
    return get_state(name).value


def clear_attributes():
    _ATTRIBUTES.clear()


def _is_array_value(value: Any) -> bool:
    if isinstance(value, (str, bytes)):
        return False
    try:
        len(value)
    except TypeError:
        return False
    return True
