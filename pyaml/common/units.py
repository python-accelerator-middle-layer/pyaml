"""
Unit handling for PyAML.

PyAML works internally with plain floats expressed in SI units (the energy is
the exception and stays in eV), which is also what the PyAT simulator uses.
`pint <https://pint.readthedocs.io>`_ is only used at the edges:

- to convert values read from / written to a control-system device whose unit
  is not the SI unit expected by PyAML (see
  :class:`~pyaml.control.si_deviceaccess.SIDeviceAccess`);
- to let users pass a :class:`pint.Quantity` to ``set()`` instead of a float
  (see :func:`to_magnitude`).

Conversions are purely multiplicative: offset units such as ``degC`` are
rejected.
"""

import re
from functools import lru_cache, wraps
from typing import Any

import numpy as np
import pint

from .exception import PyAMLConfigException, PyAMLException

# SI units in which PyAML exposes values, shared by the simulator and the control systems
SI_POSITION = "m"
SI_ANGLE = "rad"
SI_VOLTAGE = "V"
SI_FREQUENCY = "Hz"
SI_TUNE = "1"

_UREG: pint.UnitRegistry | None = None

# Strings meaning "no unit": the value is passed through unchanged.
_NO_UNIT = ("", "1", "none", "no unit", "dimensionless")


def get_registry() -> pint.UnitRegistry:
    """
    Return the application-wide pint unit registry.

    The registry is created on first use and registered with
    :func:`pint.set_application_registry`, so that ``pint.Quantity`` objects
    built by the user (or unpickled) share the PyAML registry.

    Returns
    -------
    pint.UnitRegistry
        The shared unit registry.
    """
    global _UREG
    if _UREG is None:
        _UREG = pint.get_application_registry().get()
        if not isinstance(_UREG, pint.UnitRegistry):  # pragma: no cover - defensive
            _UREG = pint.UnitRegistry()
            pint.set_application_registry(_UREG)
    return _UREG


def _is_no_unit(unit: str | None) -> bool:
    """Return ``True`` when ``unit`` means that no conversion should be done."""
    return unit is None or str(unit).strip().lower() in _NO_UNIT


# "m-1", "m-2" (accelerator notation) -> "m^-1", "m^-2"
_NEG_EXPONENT = re.compile(r"(?<=[A-Za-z\)])(-\d+)")
# "T.m" -> "T*m"
_DOT_PRODUCT = re.compile(r"(?<=[A-Za-z\)])\.(?=[A-Za-z\(])")


def normalize_unit(unit: str) -> str:
    """
    Rewrite accelerator-style unit strings in a syntax understood by pint.

    ``m-1`` becomes ``m^-1`` and ``T.m`` becomes ``T*m``. Other strings are
    returned stripped and otherwise unchanged.

    Parameters
    ----------
    unit : str
        Unit string from the configuration or a backend.

    Returns
    -------
    str
        Unit string for pint.
    """
    u = str(unit).strip()
    u = _NEG_EXPONENT.sub(r"^\1", u)
    return _DOT_PRODUCT.sub("*", u)


def _parse_unit(unit: str):
    """Parse ``unit`` with the PyAML registry, raising a PyAML exception on failure."""
    try:
        return get_registry().Unit(normalize_unit(unit))
    except Exception as e:
        raise PyAMLConfigException(f"Unknown unit '{unit}': {e}") from e


@lru_cache(maxsize=None)
def conversion_factor(src: str | None, dst: str | None) -> float:
    """
    Return the factor ``k`` such that ``value_dst = k * value_src``.

    Parameters
    ----------
    src : str or None
        Unit of the source value (typically the control-system device unit).
    dst : str or None
        Unit of the destination value (typically the SI unit used by PyAML).

    Returns
    -------
    float
        Multiplicative conversion factor. ``1.0`` when ``src`` or ``dst`` is
        empty, ``None`` or dimensionless (passthrough: the value is assumed to
        already be in the expected unit).

    Raises
    ------
    PyAMLConfigException
        If a unit is unknown to pint, if the two units have different
        dimensions, or if the conversion is not purely multiplicative.
    """
    if _is_no_unit(src) or _is_no_unit(dst) or str(src).strip() == str(dst).strip():
        return 1.0
    ureg = get_registry()
    qsrc = ureg.Quantity(1.0, _parse_unit(src))
    udst = _parse_unit(dst)
    # Compare root units rather than dimensions: pint treats rad as dimensionless,
    # so a dimension check alone would accept '%' or 'count' for an angle.
    if qsrc.to_root_units().units != ureg.Quantity(1.0, udst).to_root_units().units:
        raise PyAMLConfigException(f"Unit '{src}' cannot be converted to '{dst}'")
    try:
        k = qsrc.to(udst).magnitude
        # Reject offset units (degC, degF...): conversion of 0 must give 0
        offset = ureg.Quantity(0.0, qsrc.units).to(udst).magnitude
    except Exception as e:
        raise PyAMLConfigException(f"Unit '{src}' cannot be converted to '{dst}': {e}") from e
    if offset != 0.0:
        raise PyAMLConfigException(f"Unit conversion '{src}' -> '{dst}' is not multiplicative (offset unit)")
    return float(k)


def is_quantity(value: Any) -> bool:
    """Return ``True`` if ``value`` is a :class:`pint.Quantity`."""
    return isinstance(value, pint.Quantity)


def has_quantity(value: Any) -> bool:
    """Return ``True`` if ``value`` is a quantity or a list/tuple containing one."""
    return is_quantity(value) or (isinstance(value, (list, tuple)) and any(is_quantity(v) for v in value))


def to_magnitude(value: Any, unit: str | list[str] | None) -> Any:
    """
    Strip the unit of a user input, converting it to ``unit`` first.

    Plain numbers and arrays are returned unchanged: they are assumed to be
    already expressed in ``unit`` (SI). A :class:`pint.Quantity` (scalar or
    array) or a list of quantities is converted to ``unit`` and its magnitude
    returned.

    Parameters
    ----------
    value : object
        User input: float, array-like, :class:`pint.Quantity` or list of
        :class:`pint.Quantity`.
    unit : str or list of str or None
        Unit expected by the accessor (as returned by its ``unit()`` method).
        A list gives one unit per element of ``value``.

    Returns
    -------
    object
        ``value`` expressed as plain number(s) in ``unit``.

    Raises
    ------
    PyAMLException
        If a quantity cannot be converted to ``unit``.
    """
    if not has_quantity(value):
        return value

    if isinstance(unit, (list, tuple)) and len(set(unit)) == 1:
        unit = unit[0]

    if isinstance(unit, (list, tuple)) or not is_quantity(value):
        # One unit per element: convert element-wise (a scalar quantity is broadcast)
        units = unit if isinstance(unit, (list, tuple)) else [unit] * len(value)
        values = [value] * len(units) if is_quantity(value) and np.ndim(value.magnitude) == 0 else list(value)
        if len(units) != len(values):
            raise PyAMLException(f"Expected {len(units)} values but got {len(values)}")
        return np.array([to_magnitude(v, u) for v, u in zip(values, units, strict=True)], dtype=float)

    if _is_no_unit(unit):
        if value.dimensionless:
            return value.to("dimensionless").magnitude
        raise PyAMLException(f"Cannot assign a value in '{value.units}' to a dimensionless quantity")
    _parse_unit(unit)  # Check the target unit is valid
    try:
        # Convert with the quantity's own registry, it may not be the PyAML one
        return value.to(normalize_unit(unit)).magnitude
    except Exception as e:
        raise PyAMLException(f"Cannot convert {value} to '{unit}': {e}") from e


def accepts_quantity(method):
    """
    Decorate a ``set(self, value, ...)``-like method so that ``value`` may be a quantity.

    When ``value`` is a :class:`pint.Quantity` (or a list of them), it is
    converted to ``self.unit()`` and stripped before calling ``method``. Plain
    numbers are passed through untouched, without calling ``unit()``.

    Parameters
    ----------
    method : callable
        Method taking the value to write as first positional argument.

    Returns
    -------
    callable
        The wrapped method.
    """
    if getattr(method, "__pyaml_accepts_quantity__", False):
        return method

    @wraps(method)
    def wrapper(self, value, *args, **kwargs):
        if has_quantity(value):
            value = to_magnitude(value, self.unit())
        return method(self, value, *args, **kwargs)

    wrapper.__pyaml_accepts_quantity__ = True
    return wrapper


class AcceptsQuantity:
    """
    Mixin making ``set``/``set_and_wait`` of every subclass accept :class:`pint.Quantity` values.

    Inherited by the PyAML read/write interfaces, so that every implementation
    (including the ones of external packages) supports quantities without any
    change: the setters defined by a subclass are wrapped with
    :func:`accepts_quantity` when the subclass is created.
    """

    _QUANTITY_SETTERS = ("set", "set_and_wait")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name in cls._QUANTITY_SETTERS:
            method = cls.__dict__.get(name)
            if callable(method) and not getattr(method, "__isabstractmethod__", False):
                setattr(cls, name, accepts_quantity(method))
