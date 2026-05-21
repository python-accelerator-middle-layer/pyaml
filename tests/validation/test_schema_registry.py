"""Tests of the schema registry."""

import re
from collections.abc import Generator
from types import SimpleNamespace

import pytest

from pyaml.configuration.validation import ConfigurationSchema, SchemaRegistry, register_schema

# ==========================================================
# Dummy schemas
# ==========================================================


class DummySchema(ConfigurationSchema):
    pass


class OtherSchema(ConfigurationSchema):
    pass


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
# Singleton behaviour
# ==========================================================


def test_singleton_returns_same_instance():
    assert SchemaRegistry() is SchemaRegistry()


# ==========================================================
# Lookup
# ==========================================================


def test_getitem_returns_registered_schema(registry: SchemaRegistry):
    registry.register("pkg.module.Class", DummySchema)

    assert registry["pkg.module.Class"] is DummySchema


def test_getitem_raises_clean_keyerror_for_missing_schema(registry: SchemaRegistry):
    with pytest.raises(KeyError, match=r"No schema registered for 'pkg\.module\.Class.'"):
        _ = registry["pkg.module.Class"]


def test_get_returns_registered_schema(registry: SchemaRegistry):
    registry.register("pkg.module.Class", DummySchema)

    assert registry.get("pkg.module.Class") is DummySchema


def test_get_returns_none_for_missing_schema(registry: SchemaRegistry):
    assert registry.get("pkg.module.Class") is None


# ==========================================================
# Contents
# ==========================================================


def test_contains_returns_true_for_registered_schema(registry: SchemaRegistry):
    registry.register("pkg.module.Class", DummySchema)

    assert "pkg.module.Class" in registry


def test_contains_returns_false_for_missing_schema(registry: SchemaRegistry):
    assert "pkg.module.Class" not in registry


def test_items_returns_registered_items(registry: SchemaRegistry):
    registry.register("pkg.module.ClassA", DummySchema)
    registry.register("pkg.module.ClassB", OtherSchema)

    items = registry.items()

    assert ("pkg.module.ClassA", DummySchema) in items
    assert ("pkg.module.ClassB", OtherSchema) in items
    assert len(items) == 2


def test_keys_returns_registered_class_paths(registry: SchemaRegistry):
    registry.register("pkg.module.ClassA", DummySchema)
    registry.register("pkg.module.ClassB", OtherSchema)

    keys = registry.keys()

    assert "pkg.module.ClassA" in keys
    assert "pkg.module.ClassB" in keys
    assert len(keys) == 2


def test_values_returns_registered_schemas(registry: SchemaRegistry):
    registry.register("pkg.module.ClassA", DummySchema)
    registry.register("pkg.module.ClassB", OtherSchema)

    values = registry.values()

    assert DummySchema in values
    assert OtherSchema in values
    assert len(values) == 2


def test_len_returns_number_of_registered_schemas(registry: SchemaRegistry):
    assert len(registry) == 0

    registry.register("pkg.module.ClassA", DummySchema)
    assert len(registry) == 1

    registry.register("pkg.module.ClassB", OtherSchema)
    assert len(registry) == 2


def test_iter_returns_registered_class_paths(registry: SchemaRegistry):
    registry.register("pkg.module.ClassA", DummySchema)
    registry.register("pkg.module.ClassB", OtherSchema)

    class_paths = list(iter(registry))

    assert "pkg.module.ClassA" in class_paths
    assert "pkg.module.ClassB" in class_paths
    assert len(class_paths) == 2


# ==========================================================
# Updating
# ==========================================================


def test_update_replaces_registered_schema(registry: SchemaRegistry):
    registry.register("pkg.module.Class", DummySchema)

    registry.update("pkg.module.Class", OtherSchema)

    assert registry["pkg.module.Class"] is OtherSchema


def test_update_raises_keyerror_for_missing_schema(registry: SchemaRegistry):
    class_path = "pkg.module.Class"

    with pytest.raises(
        KeyError,
        match=re.escape(f"{class_path} is not registered."),
    ):
        registry.update(class_path, DummySchema)


def test_update_raises_typeerror_for_invalid_schema(registry: SchemaRegistry):
    with pytest.raises(
        TypeError,
        match=r"must inherit from ConfigurationSchema",
    ):
        registry.update(
            "pkg.module.Class",
            object,  # type: ignore[arg-type]
        )


# ==========================================================
# Registration
# ==========================================================


def test_register_stores_schema(registry: SchemaRegistry):
    registry.register("pkg.module.Class", DummySchema)

    assert registry["pkg.module.Class"] is DummySchema


def test_register_allows_same_schema_for_existing_class_path(registry: SchemaRegistry):
    class_path = "pkg.module.Class"

    registry.register(class_path, DummySchema)
    registry.register(class_path, DummySchema)

    assert registry[class_path] is DummySchema
    assert len(registry) == 1


def test_register_raises_valueerror_for_different_schema(registry: SchemaRegistry):
    class_path = "pkg.module.Class"

    registry.register(class_path, DummySchema)

    with pytest.raises(
        ValueError,
        match=re.escape(f"{class_path} already registered with a different schema."),
    ):
        registry.register(class_path, OtherSchema)


def test_register_raises_typeerror_for_invalid_schema(registry: SchemaRegistry):
    with pytest.raises(
        TypeError,
        match=re.escape("must inherit from ConfigurationSchema"),
    ):
        registry.register(
            "pkg.module.Class",
            object,  # type: ignore[arg-type]
        )


# ==========================================================
# Unregistering
# ==========================================================


def test_unregister_removes_registered_schema(registry: SchemaRegistry):
    class_path = "pkg.module.Class"

    registry.register(class_path, DummySchema)

    registry.unregister(class_path)

    assert class_path not in registry


def test_unregister_raises_clean_keyerror_for_missing_schema(
    registry: SchemaRegistry,
):
    class_path = "pkg.module.Class"

    with pytest.raises(
        KeyError,
        match=re.escape(f"No schema registered for '{class_path}'"),
    ):
        registry.unregister(class_path)


def test_unregister_removes_only_requested_schema(registry: SchemaRegistry):
    registry.register("pkg.module.ClassA", DummySchema)
    registry.register("pkg.module.ClassB", OtherSchema)

    registry.unregister("pkg.module.ClassA")

    assert "pkg.module.ClassA" not in registry
    assert registry["pkg.module.ClassB"] is OtherSchema
    assert len(registry) == 1


# ==========================================================
# Clearing
# ==========================================================


def test_clear_removes_all_registered_schemas(registry: SchemaRegistry):
    registry.register("pkg.module.ClassA", DummySchema)
    registry.register("pkg.module.ClassB", OtherSchema)

    registry.clear()

    assert len(registry) == 0
    assert "pkg.module.ClassA" not in registry
    assert "pkg.module.ClassB" not in registry


def test_clear_on_empty_registry_keeps_registry_empty(
    registry: SchemaRegistry,
):
    registry.clear()

    assert len(registry) == 0


def test_clear_allows_new_registrations_afterwards(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.Class", DummySchema)

    registry.clear()

    registry.register("pkg.module.OtherClass", OtherSchema)

    assert len(registry) == 1
    assert registry["pkg.module.OtherClass"] is OtherSchema


# ==========================================================
# Representation
# ==========================================================


def test_repr_returns_empty_registry_representation(
    registry: SchemaRegistry,
):
    assert repr(registry) == "SchemaRegistry({})"


def test_repr_returns_registered_schemas(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.ClassA", DummySchema)
    registry.register("pkg.module.ClassB", OtherSchema)

    result = repr(registry)

    assert result.startswith("SchemaRegistry(")
    assert "'pkg.module.ClassA'" in result
    assert "'pkg.module.ClassB'" in result

    assert f"{DummySchema.__module__}.{DummySchema.__name__}" in result
    assert f"{OtherSchema.__module__}.{OtherSchema.__name__}" in result

    assert result.endswith(")")


def test_repr_sorts_registered_class_paths(
    registry: SchemaRegistry,
):
    registry.register("pkg.module.ZClass", DummySchema)
    registry.register("pkg.module.AClass", OtherSchema)

    result = repr(registry)

    assert result.index("'pkg.module.AClass'") < result.index("'pkg.module.ZClass'")


# ==========================================================
# Validation
# ==========================================================


def test_validate_returns_registered_configuration_schema(
    registry: SchemaRegistry,
):
    class TestConfigurationSchema(ConfigurationSchema):
        class_path: str
        value: int

    class_path = "pkg.module.Class"
    registry.register(class_path, TestConfigurationSchema)

    result = registry.validate(
        {
            "class_path": class_path,
            "value": 1,
        }
    )

    assert isinstance(result, TestConfigurationSchema)
    assert result.class_path == class_path
    assert result.value == 1


# ==========================================================
# Register schema decorator
# ==========================================================


def test_register_schema_registers_the_decorated_class(
    registry: SchemaRegistry,
):
    @register_schema(DummySchema)
    class DecoratedClass:
        pass

    class_path = f"{DecoratedClass.__module__}.{DecoratedClass.__name__}"

    assert registry[class_path] is DummySchema


def test_register_schema_returns_the_original_class(
    registry: SchemaRegistry,
):
    @register_schema(DummySchema)
    class DecoratedClass:
        pass

    assert DecoratedClass.__name__ == "DecoratedClass"
    assert DecoratedClass.__module__ == __name__


def test_register_schema_can_register_multiple_classes_with_same_schema(
    registry: SchemaRegistry,
):
    @register_schema(DummySchema)
    class FirstClass:
        pass

    @register_schema(DummySchema)
    class SecondClass:
        pass

    first_path = f"{FirstClass.__module__}.{FirstClass.__name__}"
    second_path = f"{SecondClass.__module__}.{SecondClass.__name__}"

    assert registry[first_path] is DummySchema
    assert registry[second_path] is DummySchema
    assert len(registry) == 2


def test_register_schema_uses_the_class_full_path(
    registry: SchemaRegistry,
):
    @register_schema(DummySchema)
    class MyClass:
        pass

    assert f"{MyClass.__module__}.{MyClass.__name__}" in registry
