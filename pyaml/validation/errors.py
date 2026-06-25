"""Functionality for attaching location information to validation errors."""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from ..common.exception import PyAMLConfigException


@dataclass(frozen=True)
class Location:
    """
    Source location within a configuration file.

    Stores the file name together with the line and column at which a
    configuration object or field was defined.
    """

    file: str
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.file} at line {self.line}, column {self.column}."


@dataclass(frozen=True)
class LocationMetadata:
    """
    Location metadata extracted from configuration data.

    Stores the source location of a configuration object together with
    optional locations for individual configuration fields.
    """

    location: Location | None
    field_locations: dict[str, Location] | None = None


def extract_location_metadata(data: dict[str, Any]) -> tuple[dict[str, Any], LocationMetadata]:
    """
    Extract loader-added location metadata from configuration data.

    Returns a copy of the configuration dictionary with the metadata
    removed together with the extracted location information.
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


def raise_validation_error(
    exc: ValidationError,
    class_path: str,
    location_metadata: LocationMetadata | None = None,
) -> None:
    """
    Raise a configuration exception from a Pydantic validation error.

    Validation messages are formatted into a human-readable error message.
    If location metadata is available, source locations for the
    configuration object and its fields are included in the reported
    error.
    """

    messages: list[str] = []

    for err in exc.errors():
        loc = err.get("loc", ())
        msg = err["msg"]

        if len(loc) == 2:
            field, field_idx = loc
            message = f"'{field}.{field_idx}': {msg}"
            field_name = field
        elif len(loc) == 1:
            field_name = loc[0]
            message = f"'{field_name}': {msg}"
        else:
            field_name = None
            message = f"{loc}: {msg}"

        if (
            location_metadata is not None
            and location_metadata.field_locations is not None
            and field_name in location_metadata.field_locations
        ):
            message += f" ({location_metadata.field_locations[field_name]})"

        messages.append(message)

    location_str = ""
    if location_metadata is not None and location_metadata.location is not None:
        location_str = f" ({location_metadata.location})"

    raise PyAMLConfigException(f"{'; '.join(messages)} for class: '{class_path}'{location_str}") from None
