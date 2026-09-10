from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from . import abstract
from .exception import PyAMLException

if TYPE_CHECKING:
    from .holders.element_holder import ElementHolder


@dataclass(frozen=True)
class ReprOptions:
    """Limits applied to PyAML object representations."""

    max_items: int = 3
    max_depth: int = 2
    max_length: int = 800


_repr_options = ReprOptions()


def set_repr_options(
    max_items: int | None = None,
    max_depth: int | None = None,
    max_length: int | None = None,
) -> ReprOptions:
    """
    Configure the limits used by PyAML object representations.

    Passing no arguments returns the current options. Every supplied value must
    be a positive integer.
    """
    global _repr_options

    values = {
        "max_items": _repr_options.max_items if max_items is None else max_items,
        "max_depth": _repr_options.max_depth if max_depth is None else max_depth,
        "max_length": _repr_options.max_length if max_length is None else max_length,
    }
    for name, value in values.items():
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")

    _repr_options = ReprOptions(**values)
    return _repr_options


def _unavailable(error: Exception) -> str:
    return f"<unavailable: {error.__class__.__name__}>"


def _class_exclusions(obj) -> set[str]:
    exclusions: set[str] = set()
    for cls in type(obj).__mro__:
        exclusions.update(getattr(cls, "__pyaml_repr_exclude__", ()))
    return exclusions


def _properties(obj) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for cls in reversed(type(obj).__mro__):
        for name, descriptor in vars(cls).items():
            if name.startswith("_") or not isinstance(descriptor, property):
                continue
            try:
                values[name] = getattr(obj, name)
            except Exception as error:
                values[name] = _unavailable(error)
    return values


def _fields(obj) -> dict[str, Any]:
    custom_fields = getattr(obj, "_pyaml_repr_fields", None)
    if custom_fields is not None:
        try:
            return custom_fields()
        except Exception as error:
            return {"value": _unavailable(error)}

    values = _properties(obj)
    for name, value in vars(obj).items():
        if not name.startswith("_"):
            values.setdefault(name, value)
    return values


def _identity(obj) -> str:
    name = getattr(obj, "name", None)
    try:
        name = name() if callable(name) else name
    except Exception:
        name = None
    if isinstance(name, str):
        return f"{obj.__class__.__name__}:{name}"
    return obj.__class__.__name__


def _short_object_repr(obj) -> str:
    name = getattr(obj, "name", None)
    try:
        name = name() if callable(name) else name
    except Exception:
        name = None
    if isinstance(name, str):
        return f"{obj.__class__.__name__}(name={_format_value(name, 0, set())})"
    return obj.__class__.__name__


def _selected_items(values: Sequence | set) -> tuple[list[Any], int]:
    items = list(values)
    omitted = len(items) - _repr_options.max_items
    if omitted <= 0:
        return items, 0

    head_count = (_repr_options.max_items + 1) // 2
    tail_count = _repr_options.max_items - head_count
    selected = items[:head_count]
    if tail_count:
        selected.extend(items[-tail_count:])
    return selected, omitted


def _format_sequence(values: Sequence | set, depth: int, active: set[int]) -> str:
    selected, omitted = _selected_items(values)
    parts = [_format_value(value, depth, active) for value in selected]
    if omitted:
        insert_at = (_repr_options.max_items + 1) // 2
        parts.insert(insert_at, f"... +{omitted} more ...")

    if isinstance(values, tuple):
        if len(parts) == 1 and not omitted:
            return f"({parts[0]},)"
        return f"({', '.join(parts)})"
    if isinstance(values, set):
        return "{" + ", ".join(parts) + "}"
    return "[" + ", ".join(parts) + "]"


def _format_mapping(values: Mapping, depth: int, active: set[int]) -> str:
    selected, omitted = _selected_items(list(values.items()))
    parts = [f"{_format_value(key, depth, active)}: {_format_value(value, depth, active)}" for key, value in selected]
    if omitted:
        parts.insert((_repr_options.max_items + 1) // 2, f"... +{omitted} more ...")
    return "{" + ", ".join(parts) + "}"


def _format_object(obj, depth: int, active: set[int], extra_exclusions: set[str] | None = None) -> str:
    if depth >= _repr_options.max_depth:
        return _short_object_repr(obj)
    if id(obj) in active:
        return f"<recursive {obj.__class__.__name__}>"

    active.add(id(obj))
    try:
        values = _fields(obj)
        exclusions = _class_exclusions(obj)
        if extra_exclusions:
            exclusions.update(extra_exclusions)
        parts = []
        for name, value in values.items():
            if name.startswith("_") or name in exclusions or callable(value):
                continue
            if isinstance(value, (abstract.ReadFloatScalar, abstract.ReadFloatArray, abstract.ReadWriteFloatArray)):
                continue
            formatted = _identity(value) if name == "peer" and value is not None else _format_value(value, depth + 1, active)
            parts.append(f"{name}={formatted}")
        return f"{obj.__class__.__name__}({', '.join(parts)})" if parts else obj.__class__.__name__
    except Exception as error:
        return f"{obj.__class__.__name__}({_unavailable(error)})"
    finally:
        active.remove(id(obj))


def _format_value(value, depth: int, active: set[int]) -> str:
    if isinstance(value, str):
        limit = max(1, _repr_options.max_length // 4)
        suffix = "..." if len(value) > limit else ""
        return repr(value[:limit] + suffix)
    if value is None or isinstance(value, (bool, int, float, complex)):
        return repr(value)
    if isinstance(value, Mapping):
        return _format_mapping(value, depth, active)
    if isinstance(value, (list, tuple, set, frozenset)):
        return _format_sequence(value, depth, active)
    if type(value).__module__.startswith("numpy"):
        shape = getattr(value, "shape", None)
        dtype = getattr(value, "dtype", None)
        return f"{value.__class__.__name__}(shape={shape!r}, dtype={dtype!r})"
    if type(value).__module__.startswith("pyaml"):
        return _format_object(value, depth, active)
    try:
        result = repr(value)
    except Exception as error:
        return _unavailable(error)
    limit = max(1, _repr_options.max_length // 2)
    return result if len(result) <= limit else result[:limit] + "..."


def __pyaml_repr__(obj, exclude: list[str] | None = None):
    """
    Return an informative, bounded representation of a PyAML object.

    Public attributes and read-only properties are included unless they are
    excluded. Device accessors are omitted so rendering never reads a control
    system value.
    """
    result = _format_object(obj, 0, set(), set(exclude or ()))
    return result[: _repr_options.max_length] + ("..." if len(result) > _repr_options.max_length else "")


class ElementConfigModel(BaseModel):
    """
    Base class for element configuration.

    Parameters
    ----------
    name : str
        The name of the PyAML element.
    description : str, optional
        Description of the element.
    lattice_names : str or None, optional
        The name(s) of the associated element(s) in the lattice. By default,
        the PyAML element name is used. lattice_name accept the following
        syntax:
        - list(name,[name]) : Element names
        - [name]@idx[,idx] : Element indices in the subset formed by name.
        - [name]#start_idx..end_idx : Element range in the subset formed by name.
        In the above syntax, if the name is not specficied, the whole set
        of lattice element is used for indexing.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    description: str | None = None
    lattice_names: str | None = None


class Element:
    """
    Class providing access to one element of a physical or simulated lattice
    """

    __pyaml_repr_exclude__ = ("description",)

    def __init__(
        self,
        name: str,
        lattice_names: str | None = None,
        description: str | None = None,
    ):
        self._name = name
        self._lattice_names = lattice_names
        self._description = description
        self._peer: ElementHolder | None = None

    def _cfg_value(self, attr: str, fallback: Any) -> Any:
        """
        Return an attribute from _cfg if available, otherwise fallback.
        """
        cfg = getattr(self, "_cfg", None)
        if cfg is not None:
            value = getattr(cfg, attr, None)
            if value is not None:
                return value
        return fallback

    @property
    def name(self) -> str:
        return self._cfg_value("name", self._name)

    @property
    def lattice_names(self) -> str:
        cfg = getattr(self, "_cfg", None)

        if cfg is not None and cfg.lattice_names is not None:
            return cfg.lattice_names

        if self._lattice_names is not None:
            return self._lattice_names

        return self.name

    @property
    def description(self) -> str | None:
        return self._cfg_value("description", self._description)

    def get_name(self) -> str:
        """
        Returns the name of the element
        """
        return self.name

    def get_lattice_names(self) -> str | None:
        return self.lattice_names

    def get_description(self) -> str | None:
        return self.description

    def set_energy(self, E: float):
        """
        Set the instrument energy on this element
        """
        pass

    def set_mcf(self, alphac: float):
        """
        Set the instrument moment compaction factor on this element
        """
        pass

    def set_harmonic(self, h: int):
        """
        Sets the harmonic number (number of bucket) on this element
        """
        pass

    def check_peer(self):
        """
        Throws an exception if the element is not attacched
        to a simulator or to a control system
        """
        if self._peer is None:
            raise PyAMLException(f"{str(self.name)} is not attachedto a control system or the a simulator")

    @property
    def peer(self) -> "ElementHolder":
        """
        Returns the peer simulator or control system
        """
        return self._peer

    def attached_to(self) -> str:
        """
        Returns a string of which peer the element is attached to.
        """
        return "None" if self._peer is None else f"{self._peer.__class__.__name__}:{self._peer.name()}"

    def post_init(self):
        """
        Method triggered after all initialisations are done
        """
        pass

    def __repr__(self):
        return __pyaml_repr__(self)
