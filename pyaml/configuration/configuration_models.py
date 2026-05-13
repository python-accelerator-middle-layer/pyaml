"""Datamodels for the configuration."""

from pydantic import BaseModel, ConfigDict, Field


class PyAMLBaseModel(BaseModel):
    """
    Pydantic basemodel with settings
    specific for pyAML.
    """

    def model_dump(self, **kwargs):
        kwargs.setdefault(
            "serialize_as_any",
            True,
        )
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs):
        kwargs.setdefault(
            "serialize_as_any",
            True,
        )
        return super().model_dump_json(**kwargs)


class ConfigurationSchema(PyAMLBaseModel):
    """
    Schema with required fields for all
    schema classes.
    """

    model_config = ConfigDict(extra="forbid")
    class_str: str = Field(description="Class path.")
