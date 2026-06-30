"""Tests of the schema validator."""

import sys
from collections.abc import Generator
from types import ModuleType

import pytest

from pyaml.common.exception import PyAMLConfigException
from pyaml.validation import (
    ConfigurationSchema,
    SchemaRegistry,
    SchemaValidator,
)

# ==========================================================
# Dummy schemas
# ==========================================================


class DummySchema(ConfigurationSchema):
    value: int | None = None


class OtherSchema(ConfigurationSchema):
    name: str | None = None
    children: list[DummySchema] | None = None


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
# Recursive validation
# ==========================================================


def test_recursive_validate_returns_validated_schema(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.Class", DummySchema)

    data = {
        "class_path": "pkg.module.Class",
        "value": 42,
    }

    result = SchemaValidator._recursive_validate(data)

    assert isinstance(result, DummySchema)
    assert result.class_path == "pkg.module.Class"
    assert result.value == 42


def test_recursive_validate_recurses_through_nested_lists_and_dicts(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.ClassA", DummySchema)
    registry.register("pkg.module.ClassB", OtherSchema)

    data = {
        "class_path": "pkg.module.ClassB",
        "name": "dummy",
        "children": [
            {
                "class_path": "pkg.module.ClassA",
                "value": "42",
            },
            {
                "class_path": "pkg.module.ClassA",
                "value": "73",
            },
        ],
    }

    result = SchemaValidator._recursive_validate(data)

    assert isinstance(result, OtherSchema)

    assert isinstance(result.children[0], DummySchema)
    assert result.children[0].value == 42

    assert isinstance(result.children[1], DummySchema)
    assert result.children[1].value == 73


def test_recursive_validate_leaves_plain_dicts_unchanged():
    data = {
        "plain": "dict",
    }

    result = SchemaValidator._recursive_validate(data)

    assert result == data


def test_recursive_validate_leaves_non_container_values_unchanged():
    assert SchemaValidator._recursive_validate("text") == "text"
    assert SchemaValidator._recursive_validate(123) == 123
    assert SchemaValidator._recursive_validate(True) is True
    assert SchemaValidator._recursive_validate(None) is None


def test_recursive_validate_warns_for_unknown_schema(
    registry: SchemaRegistry,
):
    data = {
        "class_path": "pkg.module.Unknown",
        "value": 42,
    }

    with pytest.warns(
        UserWarning,
        match=r"Unknown schema for 'pkg\.module\.Unknown' so cannot validate\. Leaving data as raw dict\.",
    ):
        result = SchemaValidator._recursive_validate(data)

    assert result == data


# ==========================================================
# Configuration parsing
# ==========================================================


def test_parse_configuration_returns_none_for_non_configuration_dict():
    data = {
        "plain": "dict",
    }

    result = SchemaValidator._parse_configuration(data)

    assert result is None


def test_parse_configuration_accepts_modern_configuration() -> None:
    data = {
        "class_path": "pkg.module.Class",
        "value": 42,
    }

    result = SchemaValidator._parse_configuration(data)

    assert result == data


def test_parse_configuration_translates_legacy_module_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "legacy_test_module"

    module = ModuleType(module_name)
    module.PYAMLCLASS = "LegacyClass"
    monkeypatch.setitem(sys.modules, module_name, module)

    data = {
        "module": module_name,
        "value": 42,
    }

    result = SchemaValidator._parse_configuration(data)

    assert result == {
        "class_path": f"{module_name}.LegacyClass",
        "value": 42,
    }


# ==========================================================
# Top-level validation
# ==========================================================


def test_validate_returns_validated_configuration_schema(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.Class", DummySchema)

    data = {
        "class_path": "pkg.module.Class",
        "value": 42,
    }

    result = SchemaValidator.validate(data)

    assert isinstance(result, DummySchema)
    assert result.class_path == "pkg.module.Class"
    assert result.value == 42


# def test_validate_raises_typeerror_for_non_configuration_dict():
#     data = {
#         "plain": "dict",
#     }

#     with pytest.raises(
#         TypeError,
#         match=r"Top-level configuration did not validate to a ConfigurationSchema\.",
#     ):
#         SchemaValidator.validate(data)


def test_validate_to_dict_returns_dict(registry: SchemaRegistry) -> None:
    registry.register("pkg.module.Class", DummySchema)

    data = {
        "class_path": "pkg.module.Class",
        "value": 42,
    }

    result = SchemaValidator.validate_to_dict(data)

    assert result == {
        "class_path": "pkg.module.Class",
        "value": 42,
    }


# ==========================================================
# Error handling
# ==========================================================


def test_recursive_validate_includes_location_metadata_in_error(
    registry: SchemaRegistry,
) -> None:
    registry.register("pkg.module.Class", DummySchema)

    data = {
        "__location__": ("config.yaml", 10, 4),
        "__fieldlocations__": {
            "value": ("config.yaml", 11, 8),
        },
        "class_path": "pkg.module.Class",
        "value": "not-an-int",
    }

    with pytest.raises(PyAMLConfigException) as exc_info:
        SchemaValidator._recursive_validate(data)

    message = str(exc_info.value)

    assert "pkg.module.Class" in message
    assert "config.yaml at line 10, column 4." in message
    assert "config.yaml at line 11, column 8." in message
    assert "'value'" in message
