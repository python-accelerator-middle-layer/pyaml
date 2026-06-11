"""Tests of the configuration models."""

import json

import pytest
from pydantic import ValidationError
from pydantic.errors import PydanticSchemaGenerationError

from pyaml.validation import ConfigurationSchema
from pyaml.validation.models import PyAMLBaseModel


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
