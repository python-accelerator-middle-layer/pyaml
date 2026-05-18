"""Tests of the schema registry."""

from collections.abc import Generator

import pytest
from pydantic import BaseModel

from pyaml.configuration import ConfigurationSchema, SchemaRegistry, register_schema


@pytest.fixture(autouse=True)
def clear_registry() -> Generator[None, None, None]:
    """Ensure the registry is empty for each test."""
    registry = SchemaRegistry()

    # Clear before the test
    registry.clear()
    yield
    # Clear after the test
    registry.clear()


class MySchema(ConfigurationSchema):
    pass


class OtherSchema(ConfigurationSchema):
    pass


def test_register_schema() -> None:
    @register_schema(MySchema)
    class FirstClass:
        pass

    @register_schema(OtherSchema)
    class SecondClass:
        pass

    registry = SchemaRegistry()

    first_path = f"{FirstClass.__module__}.{FirstClass.__name__}"
    second_path = f"{SecondClass.__module__}.{SecondClass.__name__}"

    assert registry[first_path] is MySchema
    assert registry[second_path] is OtherSchema


def test_register_schema_raises_for_non_configuration_schema() -> None:
    class NotASchema(BaseModel):
        pass

    with pytest.raises(TypeError, match="must inherit from ConfigurationSchema"):

        @register_schema(NotASchema)  # type: ignore[arg-type]
        class MyClass:
            pass


def test_register_schema_uses_fully_qualified_class_path() -> None:
    @register_schema(MySchema)
    class MyClass:
        pass

    registry = SchemaRegistry()
    expected_key = f"{MyClass.__module__}.{MyClass.__name__}"

    assert expected_key in registry
    assert registry.get(expected_key) is MySchema
