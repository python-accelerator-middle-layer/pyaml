"""Base datamodels for configuration."""

from pydantic import BaseModel, ConfigDict, Field


class PyAMLBaseModel(BaseModel):
    """
    Base model for pyAML.

    Overrides ``model_dump()`` and ``model_dump_json()`` to enable
    ``serialize_as_any=True`` by default. This ensures that fields are
    serialized according to their runtime type rather than their declared
    annotation type.
    """

    def model_dump(self, **kwargs):
        kwargs.setdefault("serialize_as_any", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs):
        kwargs.setdefault("serialize_as_any", True)
        return super().model_dump_json(**kwargs)


class ConfigurationSchema(PyAMLBaseModel):
    """
    Base model for configuration schemas.

    Includes mandatory fields and functionality for all schemas which is to be registered in the :class:`SchemaRegistry`.
    """

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True, arbitrary_types_allowed=False, extra="forbid")

    class_path: str = Field(
        description="Fully qualified class path.",
        alias="class",
    )
