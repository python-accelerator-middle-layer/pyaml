"""Tests of validation errors."""

import pytest
from pydantic import BaseModel, ValidationError

from pyaml.common.exception import PyAMLConfigException
from pyaml.validation.errors import (
    Location,
    LocationMetadata,
    extract_location_metadata,
    raise_validation_error,
)


def test_location_str_formats_readably():
    loc = Location(file="config.yaml", line=12, column=4)
    assert str(loc) == "config.yaml at line 12, column 4."


def test_extract_location_metadata_removes_metadata_and_converts_values():
    data = {
        "__location__": ("config.yaml", 22, 3),
        "__fieldlocations__": {
            "class": ("config.yaml", 22, 10),
            "name": ("config.yaml", 23, 9),
        },
        "class": "pkg.module.Class",
        "name": "test_device",
    }

    cleaned, metadata = extract_location_metadata(data)

    assert cleaned == {
        "class": "pkg.module.Class",
        "name": "test_device",
    }
    assert metadata.location == Location("config.yaml", 22, 3)
    assert metadata.field_locations == {
        "class": Location("config.yaml", 22, 10),
        "name": Location("config.yaml", 23, 9),
    }


def test_extract_location_metadata_without_metadata_returns_clean_data():
    data = {"class": "pkg.module.Class", "name": "test_device"}

    cleaned, metadata = extract_location_metadata(data)

    assert cleaned == data
    assert metadata.location is None
    assert metadata.field_locations is None


class SimpleModel(BaseModel):
    age: int


class DeepNestedModel(BaseModel):
    items: list[SimpleModel]


def get_validation_error(model: type[BaseModel], payload: dict) -> ValidationError:
    with pytest.raises(ValidationError) as exc:
        model.model_validate(payload)
    return exc.value


def test_raise_validation_error_formats_error_with_location_metadata():
    exc = get_validation_error(SimpleModel, {"age": "not-an-int"})

    metadata = LocationMetadata(
        location=Location("config.yaml", 20, 1),
        field_locations={
            "age": Location("config.yaml", 21, 7),
        },
    )

    with pytest.raises(PyAMLConfigException) as err:
        raise_validation_error(
            exc,
            class_path="pkg.module.Class",
            location_metadata=metadata,
        )

    message = str(err.value)

    assert "'age':" in message
    assert "for class: 'pkg.module.Class'" in message
    assert "config.yaml at line 21, column 7." in message
    assert "config.yaml at line 20, column 1." in message


def test_raise_validation_error_formats_deep_nested_error_tuple_repr():
    exc = get_validation_error(DeepNestedModel, {"items": [{"age": "nope"}]})

    with pytest.raises(PyAMLConfigException) as err:
        raise_validation_error(
            exc,
            class_path="demo.DeepNestedModel",
        )

    message = str(err.value)
    assert "('items', 0, 'age'):" in message
    assert "for class: 'demo.DeepNestedModel'" in message
