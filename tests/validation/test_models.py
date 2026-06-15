"""Tests of the configuration models."""

import json

import pytest
from pydantic import BaseModel, ValidationError
from pydantic.errors import PydanticSchemaGenerationError

from pyaml.validation import ConfigurationSchema, DynamicValidation, StaticValidation
from pyaml.validation.models import PyAMLBaseModel, ValidationSchema

# ==========================================================
# PyAMLBaseModel
# ==========================================================


def test_model_dump_serializes_subclass_fields():
    class Device(PyAMLBaseModel):
        name: str

    class Magnet(Device):
        type: str

    class Accelerator(PyAMLBaseModel):
        device: Device

    accelerator = Accelerator(device=Magnet(name="QF", type="Quadrupole"))

    dumped = accelerator.model_dump()

    assert dumped == {"device": {"name": "QF", "type": "Quadrupole"}}


def test_model_dump_json_serializes_subclass_fields():
    class Device(PyAMLBaseModel):
        name: str

    class Magnet(Device):
        type: str

    class Accelerator(PyAMLBaseModel):
        device: Device

    accelerator = Accelerator(device=Magnet(name="QF", type="Quadrupole"))

    dumped_json = accelerator.model_dump_json()
    dumped = json.loads(dumped_json)

    assert dumped == {"device": {"name": "QF", "type": "Quadrupole"}}


# ==========================================================
# ConfigurationSchema
# ==========================================================


def test_configuration_schema_accepts_alias_class():
    schema = ConfigurationSchema.model_validate({"class": "pkg.module.Class"})

    assert schema.class_path == "pkg.module.Class"


def test_configuration_schema_accepts_field_name_class_path():
    schema = ConfigurationSchema.model_validate({"class_path": "pkg.module.Class"})

    assert schema.class_path == "pkg.module.Class"


def test_configuration_schema_forbids_extra_fields():
    with pytest.raises(ValidationError) as exc_info:
        ConfigurationSchema.model_validate(
            {
                "class": "pkg.module.Class",
                "unexpected": "value",
            }
        )

    assert "extra_forbidden" in str(exc_info.value)


def test_models_do_not_allow_arbitrary_types():
    class ArbitraryType:
        pass

    with pytest.raises(PydanticSchemaGenerationError):

        class TestModel(ConfigurationSchema):
            value: ArbitraryType


def test_configuration_schema_dump_uses_alias_when_requested():
    schema = ConfigurationSchema.model_validate({"class": "pkg.module.Class"})

    dumped = schema.model_dump(by_alias=True)

    assert dumped == {"class": "pkg.module.Class"}


# ==========================================================
# DynamicValidation
# ==========================================================


def test_dynamic_validation_builds_schema_from_init_signature():
    class MyClass(DynamicValidation):
        def __init__(self, name: str, count: int = 0):
            self.name = name
            self.count = count

    assert issubclass(MyClass.validation_model, ValidationSchema)
    assert list(MyClass.validation_model.model_fields) == ["name", "count"]

    name_field = MyClass.validation_model.model_fields["name"]
    count_field = MyClass.validation_model.model_fields["count"]

    assert name_field.annotation is str
    assert name_field.is_required()

    assert count_field.annotation is int
    assert count_field.default == 0


def test_dynamic_validation_accepts_positional_and_keyword_arguments():
    class MyClass(DynamicValidation):
        def __init__(self, name: str, count: int = 0):
            self.name = name
            self.count = count

    obj1 = MyClass("test", 1)
    obj2 = MyClass(name="test", count=1)
    obj3 = MyClass("test")

    assert obj1.name == "test"
    assert obj1.count == 1

    assert obj2.name == "test"
    assert obj2.count == 1

    assert obj3.name == "test"
    assert obj3.count == 0


def test_dynamic_validation_coerces_and_rejects_invalid_input():
    class MyClass(DynamicValidation):
        def __init__(self, name: str, count: int):
            self.name = name
            self.count = count

    obj = MyClass(name="test", count="12")
    assert obj.count == 12

    with pytest.raises(ValidationError):
        MyClass(name="test", count="not-an-int")


def test_dynamic_validation_rejects_manual_validation_model():
    class ManualModel(BaseModel):
        name: str

    with pytest.raises(TypeError, match="may not define validation_model manually"):

        class Broken(DynamicValidation):
            validation_model = ManualModel

            def __init__(self, name: str):
                self.name = name


# ==========================================================
# StaticValidation
# ==========================================================


def test_static_validation_accepts_explicit_basemodel():
    class ExampleSchema(BaseModel):
        name: str
        count: int = 0

    class Example(StaticValidation):
        validation_model = ExampleSchema

        def __init__(self, name: str, count: int = 0):
            self.name = name
            self.count = count

    obj1 = Example("test", 1)
    obj2 = Example(name="test", count=1)
    obj3 = Example("test")

    assert obj1.name == "test"
    assert obj1.count == 1

    assert obj2.name == "test"
    assert obj2.count == 1

    assert obj3.name == "test"
    assert obj3.count == 0


def test_static_validation_validates_and_coerces_input():
    class ExampleSchema(BaseModel):
        name: str
        count: int

    class Example(StaticValidation):
        validation_model = ExampleSchema

        def __init__(self, name: str, count: int):
            self.name = name
            self.count = count

    obj = Example(name="test", count="12")
    assert obj.count == 12

    with pytest.raises(ValidationError):
        Example(name="test", count="not-an-int")


def test_static_validation_inherits_validation_model():
    class ParentSchema(BaseModel):
        name: str

    class Parent(StaticValidation):
        validation_model = ParentSchema

        def __init__(self, name: str):
            self.name = name

    class Child(Parent):
        def __init__(self, name: str):
            super().__init__(name)

    obj = Child("test")
    assert obj.name == "test"
    assert Child.validation_model is ParentSchema


def test_static_validation_requires_a_validation_model():
    with pytest.raises(TypeError, match="must define validation_model"):

        class Broken(StaticValidation):
            def __init__(self, name: str):
                self.name = name
