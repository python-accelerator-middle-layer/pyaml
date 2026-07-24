"""Tests of the schema generator."""

import json
import re
from collections.abc import Generator
from pathlib import Path

import pytest
from pydantic import Field

from pyaml.validation import (
    ConfigurationSchema,
    SchemaGenerator,
    SchemaRegistry,
)
from pyaml.validation.generator import RegistryJsonSchema

# ==========================================================
# Dummy schemas
# ==========================================================


class DummySchema(ConfigurationSchema):
    pass


class OtherSchema(ConfigurationSchema):
    pass


class ParentSchema(ConfigurationSchema):
    """Parent schema used to test inheritance."""

    pass


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
# Registry-aware polymorphism
# ==========================================================


def test_generate_replaces_parent_schema_with_registered_subclasses(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.Parent", ParentSchema)
    registry.register("pkg.module.ChildA", ChildSchemaA)
    registry.register("pkg.module.ChildB", ChildSchemaB)

    schema = SchemaGenerator.generate("pkg.module.Parent")

    child_refs = {item["$ref"] for item in schema.get("anyOf", [])}

    assert "#/$defs/ChildSchemaA" in child_refs
    assert "#/$defs/ChildSchemaB" in child_refs


def test_model_schema_preserves_metadata_from_parent_schema(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.Parent", ParentSchema)
    registry.register("pkg.module.ChildA", ChildSchemaA)
    registry.register("pkg.module.ChildB", ChildSchemaB)

    generator = RegistryJsonSchema()
    base_schema = ParentSchema.__pydantic_core_schema__

    schema = generator.model_schema(base_schema)

    assert schema["title"] == "ParentSchema"


# ==========================================================
# Literals
# ==========================================================


def test_add_literals_to_class_path_ignores_empty_literal_list():
    schema = {"type": "string"}

    RegistryJsonSchema._add_literals_to_class_path(schema, [])

    assert schema == {"type": "string"}


def test_add_literals_to_class_path_replaces_single_value_with_const():
    schema = {"type": "string"}

    RegistryJsonSchema._add_literals_to_class_path(
        schema,
        ["pkg.module.Parent"],
    )

    assert schema["const"] == "pkg.module.Parent"
    assert "enum" not in schema


def test_add_literals_to_class_path_merges_existing_enum_and_removes_duplicates():
    schema = {"type": "string", "enum": ["pkg.module.Parent", "pkg.module.ChildA"]}

    RegistryJsonSchema._add_literals_to_class_path(
        schema,
        ["pkg.module.ChildA", "pkg.module.ChildB", "pkg.module.Parent"],
    )

    assert schema["enum"] == [
        "pkg.module.Parent",
        "pkg.module.ChildA",
        "pkg.module.ChildB",
    ]
    assert "const" not in schema


def test_add_literals_to_class_path_does_not_modify_non_string_schema_without_enum():
    schema = {"type": "integer"}

    RegistryJsonSchema._add_literals_to_class_path(schema, ["pkg.module.Parent"])

    assert schema == {"type": "integer"}


def test_add_literals_to_class_path_updates_existing_enum_even_without_string_type():
    schema = {"enum": ["pkg.module.Parent"]}

    RegistryJsonSchema._add_literals_to_class_path(schema, ["pkg.module.ChildA"])

    assert schema["enum"] == ["pkg.module.Parent", "pkg.module.ChildA"]
    assert "const" not in schema
