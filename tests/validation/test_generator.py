"""Tests of the schema generator."""

import json
import re
from collections.abc import Generator
from pathlib import Path

import pytest
from pydantic import Field

from pyaml.configuration.validation import (
    ConfigurationSchema,
    SchemaGenerator,
    SchemaRegistry,
)
from pyaml.configuration.validation.generator import RegistryJsonSchema

# ==========================================================
# Dummy schemas
# ==========================================================


class DummySchema(ConfigurationSchema):
    pass


class OtherSchema(ConfigurationSchema):
    pass


class ParentSchema(ConfigurationSchema):
    """Parent schema used to test registry-based oneOf generation."""


class ChildSchemaA(ParentSchema):
    a: int = 1


class ChildSchemaB(ParentSchema):
    b: str = "x"


class ContainerSchema(ConfigurationSchema):
    model: ChildSchemaA | None = Field(
        default=None,
        description="Container schema used for testing.",
    )


# ==========================================================
# Fixtures
# ==========================================================


@pytest.fixture(autouse=True)
def clear_registry() -> Generator[None, None, None]:
    """Ensure the registry is empty for each test."""

    registry = SchemaRegistry()
    registry.clear()
    yield
    registry.clear()


@pytest.fixture
def registry() -> SchemaRegistry:
    return SchemaRegistry()


# ==========================================================
# Save
# ==========================================================


def test_save_writes_schema_to_file(registry: SchemaRegistry, tmp_path: Path):
    class_path = "pkg.module.Class"
    registry.register(class_path, DummySchema)

    filename = tmp_path / "schema.json"

    result = SchemaGenerator.save(class_path, filename, indent=2)

    assert result == filename
    assert json.loads(filename.read_text(encoding="utf-8")) == SchemaGenerator.generate(class_path)


# ==========================================================
# Generate
# ==========================================================


def test_generate_raises_clean_keyerror_for_missing_schema(registry: SchemaRegistry):
    class_path = "pkg.module.Class"

    with pytest.raises(
        KeyError,
        match=re.escape(f"No schema registered for '{class_path}'"),
    ):
        SchemaGenerator.generate(class_path)


def test_generate_returns_schema_for_registered_class(registry: SchemaRegistry):
    class_path = "pkg.module.Class"

    registry.register(class_path, DummySchema)

    schema = SchemaGenerator.generate(class_path)

    assert schema["title"] == "DummySchema"


# ==========================================================
# Registry-aware polymorphism
# ==========================================================


def test_generate_replaces_parent_schema_with_oneof_over_registered_subclasses(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.Parent", ParentSchema)
    registry.register("pkg.module.ChildA", ChildSchemaA)
    registry.register("pkg.module.ChildB", ChildSchemaB)

    schema = SchemaGenerator.generate("pkg.module.Parent")

    assert "oneOf" in schema
    assert "anyOf" not in schema
    assert len(schema["oneOf"]) == 2


def test_model_schema_preserves_metadata_from_parent_schema(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.Parent", ParentSchema)
    registry.register("pkg.module.ChildA", ChildSchemaA)
    registry.register("pkg.module.ChildB", ChildSchemaB)

    generator = RegistryJsonSchema()
    base_schema = ParentSchema.__pydantic_core_schema__

    schema = generator.model_schema(base_schema)

    assert "oneOf" in schema
    assert schema["title"] == "ParentSchema"


# ==========================================================
# Union normalization
# ==========================================================


def test_get_union_of_schemas_rewrites_anyof_to_oneof():
    generator = RegistryJsonSchema()

    schema = generator.get_union_of_schemas(
        [
            {"type": "string"},
            {"type": "null"},
        ]
    )

    assert "oneOf" in schema
    assert "anyOf" not in schema
    assert schema["oneOf"] == [
        {"type": "string"},
        {"type": "null"},
    ]


def test_generate_uses_custom_union_handling_for_nullable_model(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.Container", ContainerSchema)

    schema = SchemaGenerator.generate("pkg.module.Container")

    model_schema = schema["properties"]["model"]

    assert "oneOf" in model_schema
    assert "anyOf" not in model_schema
    assert model_schema["default"] is None
    assert model_schema["description"] == "Container schema used for testing."
