"""Tests of the schema builder."""

import inspect
from abc import ABC
from collections.abc import Generator
from enum import Enum
from typing import Annotated, Any, Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, Field

from pyaml.validation.configuration_models import ConfigurationSchema
from pyaml.validation.registry import SchemaRegistry
from pyaml.validation.schema_builder import (
    EXCLUDED_TYPES,
    _configuration_schema_from_basemodel,
    _field_definition_from_field_info,
    _fields_from_constructor_signature,
    _generate_schema_name,
    _resolve_annotation,
    generate_configuration_schema,
)


@pytest.fixture(autouse=True)
def clear_registry() -> Generator[None, None, None]:
    """Ensure the registry is empty for each test."""

    registry = SchemaRegistry()
    registry.clear()
    yield
    registry.clear()


class Color(Enum):
    RED = "red"


def test_generate_schema_name():
    class Magnet:
        pass

    assert _generate_schema_name(Magnet) == "MagnetConfigurationSchema"


def test_generate_configuration_schema_requires_class():
    with pytest.raises(TypeError, match="Source must be a class"):
        generate_configuration_schema(1)


def test_generate_configuration_schema_from_validation_model():
    class ValidationModel(BaseModel):
        strength: int
        name: str = "Q1"

    class Magnet:
        validation_model = ValidationModel

    schema = generate_configuration_schema(Magnet)

    assert issubclass(schema, ConfigurationSchema)
    assert schema.__name__ == "MagnetConfigurationSchema"
    assert schema.model_fields["strength"].annotation is int
    assert schema.model_fields["name"].default == "Q1"

    registry = SchemaRegistry()
    assert registry.get(f"{Magnet.__module__}.{Magnet.__name__}") is schema


def test_generate_configuration_schema_from_constructor():
    class Magnet:
        def __init__(self, strength: int, name: str = "Q1"):
            pass

    schema = generate_configuration_schema(Magnet)

    assert issubclass(schema, ConfigurationSchema)
    assert schema.model_fields["strength"].annotation is int
    assert schema.model_fields["name"].default == "Q1"

    registry = SchemaRegistry()
    assert registry.get(f"{Magnet.__module__}.{Magnet.__name__}") is schema


def test_generate_configuration_schema_is_cached():
    class Magnet:
        def __init__(self, strength: int):
            pass

    schema1 = generate_configuration_schema(Magnet)
    schema2 = generate_configuration_schema(Magnet)

    assert schema1 is schema2


def test_configuration_schema_from_basemodel_rejects_reserved_field():
    class ValidationModel(BaseModel):
        class_path: str

    with pytest.raises(ValueError, match="reserved field"):
        _configuration_schema_from_basemodel(
            ValidationModel,
            "BadConfigurationSchema",
            __name__,
        )


def test_generate_configuration_schema_registers_parent_chain():
    class Curve:
        pass

    class Curve1(Curve):
        pass

    class Curve2(Curve1):
        pass

    curve2_schema = generate_configuration_schema(Curve2)

    registry = SchemaRegistry()
    curve_path = f"{Curve.__module__}.{Curve.__name__}"
    curve1_path = f"{Curve1.__module__}.{Curve1.__name__}"
    curve2_path = f"{Curve2.__module__}.{Curve2.__name__}"

    curve_schema = registry.get(curve_path)
    curve1_schema = registry.get(curve1_path)
    curve2_schema_from_registry = registry.get(curve2_path)

    assert curve_schema is not None
    assert curve1_schema is not None
    assert curve2_schema_from_registry is curve2_schema

    assert curve1_schema.is_virtual_subclass_of(curve_schema)
    assert curve2_schema.is_virtual_subclass_of(curve1_schema)
    assert curve2_schema.is_virtual_subclass_of(curve_schema)
    assert not curve_schema.is_virtual_subclass_of(curve1_schema)


def test_generate_configuration_schema_registers_multiple_inheritance():
    class Curve:
        pass

    class Monitor:
        pass

    class Curve1(Curve):
        pass

    class Curve2(Curve1, Monitor):
        pass

    curve2_schema = generate_configuration_schema(Curve2)

    registry = SchemaRegistry()
    curve_schema = registry.get(f"{Curve.__module__}.{Curve.__name__}")
    monitor_schema = registry.get(f"{Monitor.__module__}.{Monitor.__name__}")
    curve1_schema = registry.get(f"{Curve1.__module__}.{Curve1.__name__}")
    curve2_schema_from_registry = registry.get(f"{Curve2.__module__}.{Curve2.__name__}")

    assert curve_schema is not None
    assert monitor_schema is not None
    assert curve1_schema is not None
    assert curve2_schema_from_registry is curve2_schema

    assert curve1_schema.is_virtual_subclass_of(curve_schema)
    assert curve2_schema.is_virtual_subclass_of(curve1_schema)
    assert curve2_schema.is_virtual_subclass_of(curve_schema)
    assert curve2_schema.is_virtual_subclass_of(monitor_schema)


def test_fields_from_constructor_signature():
    class Example:
        def __init__(self, x: int, y: str = "a", *args, **kwargs):
            pass

    fields = _fields_from_constructor_signature(Example)

    assert fields["x"] == (int, ...)
    assert fields["y"] == (str, "a")
    assert set(fields) == {"x", "y"}


def test_fields_from_constructor_signature_rejects_reserved_parameter():
    class Example:
        def __init__(self, class_path: str):
            pass

    with pytest.raises(ValueError, match="reserved parameter"):
        _fields_from_constructor_signature(Example)


def test_resolve_annotation():
    assert _resolve_annotation(inspect._empty) is Any
    assert _resolve_annotation(Any) is Any
    assert _resolve_annotation(None) is type(None)
    assert _resolve_annotation(int) is int
    assert _resolve_annotation(Color) is Color
    assert _resolve_annotation(list[int]) == list[int]
    assert _resolve_annotation(dict[str, int]) == dict[str, int]
    assert _resolve_annotation(tuple[int, ...]) == tuple[int, ...]
    assert _resolve_annotation(tuple[int, str]) == tuple[int, str]
    assert _resolve_annotation(set[int]) == set[int]
    assert _resolve_annotation(frozenset[int]) == frozenset[int]
    assert _resolve_annotation(int | str) == (int | str)
    assert _resolve_annotation(Literal["a", "b"]) == Literal["a", "b"]

    annotated = _resolve_annotation(Annotated[int, "meta"])
    assert get_origin(annotated) is Annotated
    assert get_args(annotated) == (int, "meta")


def test_excluded_framework_bases_are_not_registered():
    class FrameworkConfig(ABC):
        pass

    class UserConfig(FrameworkConfig):
        pass

    EXCLUDED_TYPES.add(FrameworkConfig)
    try:
        generate_configuration_schema(UserConfig)
        registry = SchemaRegistry()
        assert f"{FrameworkConfig.__module__}.{FrameworkConfig.__name__}" not in registry
        assert f"{UserConfig.__module__}.{UserConfig.__name__}" in registry
    finally:
        EXCLUDED_TYPES.remove(FrameworkConfig)


def test_resolve_annotation_rejects_forward_reference():
    with pytest.raises(TypeError, match="Forward references"):
        _resolve_annotation("SomeClass")


def test_field_definition_from_field_info():
    class Model(BaseModel):
        x: int = Field(
            default_factory=lambda: 5,
            description="desc",
            title="title",
            examples=[1],
            deprecated=True,
            alias="alias",
        )

    annotation, field = _field_definition_from_field_info(
        "x",
        Model.model_fields["x"],
    )

    assert annotation is int
    assert field.default_factory is not None
    assert field.alias == "alias"
    assert field.description == "desc"
    assert field.title == "title"
    assert field.examples == [1]
    assert field.deprecated is True
