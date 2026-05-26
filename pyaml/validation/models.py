"""Datamodels for the validating the configuration."""

import importlib
from typing import ClassVar

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PyAMLBaseModel(BaseModel):
    """
    Pydantic base model with settings
    specific for pyAML.
    """

    def model_dump(self, **kwargs):
        kwargs.setdefault("serialize_as_any", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs):
        kwargs.setdefault("serialize_as_any", True)
        return super().model_dump_json(**kwargs)


class ConfigurationSchema(PyAMLBaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True, arbitrary_types_allowed=False, extra="forbid")

    CLASS_PATH_ALIASES: ClassVar[tuple[str, ...]] = ("class",)

    class_path: str = Field(
        description="Fully qualified class path.",
        validation_alias=AliasChoices(*CLASS_PATH_ALIASES),
    )


class ModuleConfigurationSchema(PyAMLBaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True, extra="forbid")

    MODULE_PATH_ALIASES: ClassVar[tuple[str, ...]] = ("module", "type")

    module_path: str = Field(
        description="Fully qualified module path.",
        validation_alias=AliasChoices(*MODULE_PATH_ALIASES),
    )

    def to_configuration(self) -> ConfigurationSchema:
        module = importlib.import_module(self.module_path)

        try:
            class_name = module.PYAMLCLASS
        except AttributeError as e:
            raise ValueError(f"Module '{self.module_path}' does not define PYAMLCLASS.") from e

        return ConfigurationSchema(class_path=f"{self.module_path}.{class_name}")
