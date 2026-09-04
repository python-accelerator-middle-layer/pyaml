"""Functionality for attaching location information to validation errors."""

from dataclasses import dataclass
from typing import Any, NoReturn

from pydantic import ValidationError

from ..common.exception import PyAMLConfigException


@dataclass(frozen=True)
class Location:
    """
    Source location within a configuration file.

    Parameters
    ----------
    file : str
        Name of the configuration file.
    line : int
        Line number where the object or field was defined.
    column : int
        Column number where the object or field was defined.
    """

    file: str
    line: int
    column: int

    def __str__(self) -> str:
        """
        Return a human-readable string representation of the object.

        Returns
        -------
        str
            Result produced by the operation.
        """
        return f"{self.file}: line {self.line}, column {self.column}"


@dataclass(frozen=True)
class LocationMetadata:
    """
    Location metadata extracted from configuration data.

    Parameters
    ----------
    location : Location | None
        Source location of the configuration object itself.
    field_locations : dict[str, Location] | None, optional
        Source locations for individual configuration fields.
    """

    location: Location | None
    field_locations: dict[str, Location] | None = None


def extract_location_metadata(data: dict[str, Any]) -> tuple[dict[str, Any], LocationMetadata]:
    """
    Extract loader-added location metadata from configuration data.

    Parameters
    ----------
    data : dict[str, Any]
        Configuration data potentially containing loader-added metadata.

    Returns
    -------
    tuple[dict[str, Any], LocationMetadata]
        A copy of the configuration dictionary with the metadata removed,
        together with the extracted location information.
    """

    cleaned = dict(data)

    # Get the location
    raw_location = cleaned.pop("__location__", None)
    location = Location(*raw_location) if raw_location is not None else None

    # Get the field locations
    raw_field_locations = cleaned.pop("__fieldlocations__", None)
    field_locations = (
        {field: Location(*raw_loc) for field, raw_loc in raw_field_locations.items()}
        if raw_field_locations is not None
        else None
    )

    return cleaned, LocationMetadata(
        location=location,
        field_locations=field_locations,
    )


def _format_value(value: Any, max_len: int = 120) -> str:
    """
    Format a value for inclusion in an error message.

    Parameters
    ----------
    value : Any
        Value to format.
    max_len : int, optional
        Maximum length of the formatted representation, by default 120.

    Returns
    -------
    str
        Formatted value string.
    """

    text = repr(value)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def _format_location_path(loc: tuple[Any, ...]) -> str:
    """
    Format a Pydantic error location as a human-readable path.

    Parameters
    ----------
    loc : tuple[Any, ...]
        Location tuple from a Pydantic validation error.

    Returns
    -------
    str
        Human-readable location path such as ``items[0].name``.
        Returns ``<root>`` for an empty location.
    """

    parts: list[str] = []

    for item in loc:
        if isinstance(item, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{item}]"
            else:
                parts.append(f"[{item}]")
        else:
            parts.append(str(item))

    return ".".join(parts) if parts else "<root>"


def raise_validation_error(
    exc: ValidationError,
    class_path: str,
    location_metadata: LocationMetadata | None = None,
) -> NoReturn:
    """
    Raise a configuration exception from a Pydantic validation error.

    Parameters
    ----------
    exc : ValidationError
        Validation error raised by Pydantic.
    class_path : str
        Fully qualified class path of the configuration object being validated.
    location_metadata : LocationMetadata | None, optional
        Source location metadata extracted from the configuration data, by
        default None.

    Raises
    ------
    PyAMLConfigException
        Always raised with a formatted human-readable error message.
    """

    header = [f"Validation failed for class: '{class_path}'"]

    if location_metadata is not None and location_metadata.location is not None:
        header.append(f"at {location_metadata.location}.")

    else:
        header[-1] += "."

    error_lines: list[str] = []

    for err in exc.errors():
        loc = tuple(err.get("loc", ()))
        msg = err["msg"]
        bad_value = err.get("input", None)

        path = _format_location_path(loc)
        error_lines.append(f"Field '{path}' is invalid:")
        error_lines.append(f"  error: {msg}")

        if bad_value is not None:
            error_lines.append(f"  got: {_format_value(bad_value)}")

        field_name = loc[0] if loc else None
        if (
            location_metadata is not None
            and location_metadata.field_locations is not None
            and field_name in location_metadata.field_locations
        ):
            error_lines.append(f"  location: {location_metadata.field_locations[field_name]}")

    if header[-1].endswith("."):
        message = "\n".join(header + error_lines)
    else:
        message = f"{header[0]} {' '.join(header[1:])} {error_lines[0]}\n" + "\n".join(error_lines[1:])

    raise PyAMLConfigException(message) from None
