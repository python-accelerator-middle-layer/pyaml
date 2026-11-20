"""
Unit handling for PyAML.

PyAML works internally with plain floats expressed in SI units (the energy is
the exception and stays in eV), which is also what the PyAT simulator uses.
`pint <https://pint.readthedocs.io>`_ is only used at the edges:

- to convert values read from / written to a control-system device whose unit
  is not the SI unit expected by PyAML (see
  :class:`~pyaml.control.si_deviceaccess.SIDeviceAccess`);
- to let users pass a :class:`pint.Quantity` to ``set()`` instead of a float
  (see :func:`to_magnitude`);
- optionally, to return a :class:`pint.Quantity` from ``get(quantity=True)``
  (see :func:`to_quantity`). ``get()`` returns plain floats by default.

Conversions are purely multiplicative: offset units such as ``degC`` are
rejected.

Unit strings
------------
Units accepted in configurations (magnet models, devices) and reported by the
control-system backends:

- any unit expression understood by pint: unit symbols or names, with SI
  prefixes, combined with ``*``, ``/`` and ``**`` or ``^`` for powers, e.g.
  ``mm``, ``MHz``, ``kV``, ``mrad``, ``deg``, ``1/m**2``, ``T*m``;
- the accelerator notations ``m-1``, ``m-2`` (negative exponent) and ``T.m``
  (product), see :func:`normalize_unit`;
- ``""``, ``"none"`` or ``"No unit"``: no unit given, the value is assumed to
  already be in the unit expected by PyAML (no conversion);
- ``"1"`` or ``"dimensionless"``: dimensionless value.

Units reported by ``unit()`` and ``control_system_unit()`` are in a canonical
form, pint's compact abbreviated format (see :func:`format_unit`), so that two
spellings of the same unit compare equal: ``m-1``, ``1/m`` and ``m^-1`` are all
reported as ``1/m``, ``m-2`` as ``1/m**2``, ``T.m`` as ``m*T``, ``um`` as
``μm``; dimensionless values as ``"1"`` and a device without unit as ``""``.
"""

import re
from functools import cache, wraps
from typing import Any

import numpy as np
import pint

from .exception import PyAMLConfigException, PyAMLException

# Units used by PyAML (interally and used by get/set methods).
SI_POSITION = "m"
SI_ANGLE = "rad"
SI_VOLTAGE = "V"
SI_FREQUENCY = "Hz"
SI_TUNE = "1"

_UREG: pint.UnitRegistry | None = None

# Strings meaning "no unit given" and "dimensionless": the value is passed through unchanged.
_NOT_GIVEN = ("", "none", "no unit")
_DIMENSIONLESS = ("1", "dimensionless")
_NO_UNIT = _NOT_GIVEN + _DIMENSIONLESS


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
    returned stripped and otherwise unchanged. See the "Unit strings" section
    of :mod:`pyaml.common.units` for the accepted formats.

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


@cache
def format_unit(unit: str | None) -> str | None:
    """
    Return the canonical form of a unit string.

    The canonical form is pint's compact abbreviated format (``~C``): ``m-1``,
    ``1/m`` and ``m^-1`` all give ``1/m``, ``T.m`` gives ``m*T``.

    Parameters
    ----------
    unit : str or None
        Unit string, in any of the formats accepted by PyAML (see the "Unit
        strings" section of :mod:`pyaml.common.units`).

    Returns
    -------
    str or None
        ``"1"`` for a dimensionless unit, ``""`` when no unit is given,
        ``None`` for ``None``. A string that pint cannot parse is returned
        stripped, unchanged.
    """
    if unit is None:
        return None
    u = str(unit).strip()
    if u.lower() in _NOT_GIVEN:
        return ""
    if u.lower() in _DIMENSIONLESS:
        return "1"
    try:
        parsed = _parse_unit(u)
    except PyAMLConfigException:
        return u
    return format(parsed, "~C") or "1"


@cache
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
        Multiplicative conversion factor. ``1.0`` when ``src`` is empty,
        ``None`` or dimensionless (passthrough: the value is assumed to
        already be in the expected unit). An empty ``dst`` means
        dimensionless: ``src`` must then be dimensionless too (``%``...).

    Raises
    ------
    PyAMLConfigException
        If a unit is unknown to pint, if the two units have different
        dimensions, or if the conversion is not purely multiplicative.
    """
    if _is_no_unit(src) or str(src).strip() == str(dst).strip():
        return 1.0
    ureg = get_registry()
    qsrc = ureg.Quantity(1.0, _parse_unit(src))
    udst = ureg.dimensionless if _is_no_unit(dst) else _parse_unit(dst)
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


def is_frequency_unit(unit: str | None) -> bool:
    """
    Return ``True`` if ``unit`` is a frequency unit (``Hz``, ``kHz``, ``1/s``...).

    Parameters
    ----------
    unit : str or None
        Unit string, in any of the formats accepted by PyAML.

    Returns
    -------
    bool
        ``False`` for an empty, dimensionless, unknown or non-frequency unit.
    """
    if _is_no_unit(unit):
        return False
    try:
        conversion_factor(unit, SI_FREQUENCY)
    except PyAMLConfigException:
        return False
    return True


def is_quantity(value: Any) -> bool:
    """Return ``True`` if ``value`` is a :class:`pint.Quantity`."""
    return isinstance(value, pint.Quantity)


def has_quantity(value: Any) -> bool:
    """Return ``True`` if ``value`` is a quantity or a list/tuple containing one."""
    return is_quantity(value) or (isinstance(value, (list, tuple)) and any(is_quantity(v) for v in value))


def common_unit(units: list) -> str | list | None:
    """
    Return the unit shared by all values, or the per-value units if they differ.

    Accessors report a single unit when all their values share it, and one
    unit per value only when the units genuinely differ (e.g. strengths of
    different multipoles).

    Parameters
    ----------
    units : list
        One unit per value, possibly nested to follow the shape of ``get()``.
        ``None`` entries (no device behind a value) are ignored.

    Returns
    -------
    str or list or None
        The shared unit, ``units`` unchanged if they differ, ``None`` if
        there is no unit at all.
    """

    def _flatten(items):
        for u in items:
            if isinstance(u, (list, tuple)):
                yield from _flatten(u)
            elif u is not None:
                yield u

    flat = list(_flatten(units))
    if not flat:
        return None
    return flat[0] if len(set(flat)) == 1 else units


def per_value_units(unit: str | list[str] | None, n: int) -> list:
    """
    Expand the ``unit()`` of an accessor of ``n`` values to one unit per value.

    Parameters
    ----------
    unit : str or list of str or None
        Unit as returned by ``unit()`` or ``control_system_unit()``.
    n : int
        Number of values of the accessor.

    Returns
    -------
    list
        ``n`` units.

    Raises
    ------
    PyAMLException
        If ``unit`` is a list whose length is not ``n``.
    """
    if not isinstance(unit, (list, tuple)):
        return [unit] * n
    if len(unit) != n:
        raise PyAMLException(f"Expected {n} units but got {len(unit)}")
    return list(unit)


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


def to_quantity(value: Any, unit: str | list[str] | None) -> Any:
    """
    Attach ``unit`` to a value returned by ``get()``.

    Parameters
    ----------
    value : object
        Float, array-like or ``None``, expressed in ``unit``.
    unit : str or list of str or None
        Unit of ``value`` (as returned by the accessor's ``unit()`` method),
        either one for all values or one per element of ``value``.

    Returns
    -------
    pint.Quantity or list of pint.Quantity or None
        A single quantity when all values share the same unit. A list of
        quantities, one per element, when the units differ (a pint array
        cannot hold several units). ``None`` when ``value`` is ``None``.

    Raises
    ------
    PyAMLException
        If ``unit`` is unknown or if the number of units does not match ``value``.
    """
    if value is None:
        return None
    if isinstance(unit, (list, tuple)):
        if len(set(unit)) > 1:
            if len(unit) != len(value):
                raise PyAMLException(f"Expected {len(unit)} values but got {len(value)}")
            return [to_quantity(v, u) for v, u in zip(value, unit, strict=True)]
        unit = unit[0] if unit else None
    ureg = get_registry()
    try:
        u = ureg.dimensionless if _is_no_unit(unit) else _parse_unit(unit)
    except PyAMLConfigException as e:
        raise PyAMLException(str(e)) from e
    magnitude = float(value) if np.ndim(value) == 0 else np.asarray(value, dtype=float)
    return ureg.Quantity(magnitude, u)


def returns_quantity(method):
    """
    Decorate a ``get(self, ...)``-like method with an optional ``quantity`` keyword.

    ``method(..., quantity=True)`` returns the value as a :class:`pint.Quantity`
    in ``self.unit()`` (see :func:`to_quantity`). By default (``quantity=False``)
    the value is returned untouched, without calling ``unit()``.

    Parameters
    ----------
    method : callable
        Method returning values expressed in ``self.unit()``.

    Returns
    -------
    callable
        The wrapped method.
    """
    if getattr(method, "__pyaml_returns_quantity__", False):
        return method

    @wraps(method)
    def wrapper(self, *args, quantity: bool = False, **kwargs):
        value = method(self, *args, **kwargs)
        return to_quantity(value, self.unit()) if quantity else value

    wrapper.__pyaml_returns_quantity__ = True
    return wrapper


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


def formats_unit(method):
    """
    Decorate a ``unit(self)``-like method so that it returns canonical unit strings.

    The result (a unit, ``None`` or a possibly nested list of them) is passed
    through :func:`format_unit`.

    Parameters
    ----------
    method : callable
        Method returning unit string(s).

    Returns
    -------
    callable
        The wrapped method.
    """
    if getattr(method, "__pyaml_formats_unit__", False):
        return method

    def _format(unit):
        return [_format(u) for u in unit] if isinstance(unit, (list, tuple)) else format_unit(unit)

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        return _format(method(self, *args, **kwargs))

    wrapper.__pyaml_formats_unit__ = True
    return wrapper


class AcceptsQuantity:
    """
    Mixin adding :class:`pint.Quantity` support to every subclass.

    - ``set``/``set_and_wait`` accept quantities, converted to ``unit()``
      (see :func:`accepts_quantity`);
    - ``get`` accepts an optional ``quantity=True`` keyword returning a
      quantity in ``unit()`` (see :func:`returns_quantity`). The default
      still returns plain floats;
    - ``unit``/``control_system_unit`` return canonical unit strings (see
      :func:`formats_unit`), so that two spellings of the same unit compare
      equal.

    Inherited by the PyAML read/write interfaces, so that every implementation
    (including the ones of external packages) supports quantities without any
    change: the methods defined by a subclass are wrapped when the subclass is
    created.
    """

    _QUANTITY_SETTERS = ("set", "set_and_wait")
    _QUANTITY_GETTERS = ("get",)
    _UNIT_METHODS = ("unit", "control_system_unit")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for names, decorator in (
            (cls._QUANTITY_SETTERS, accepts_quantity),
            (cls._QUANTITY_GETTERS, returns_quantity),
            (cls._UNIT_METHODS, formats_unit),
        ):
            for name in names:
                method = cls.__dict__.get(name)
                if callable(method) and not getattr(method, "__isabstractmethod__", False):
                    setattr(cls, name, decorator(method))
