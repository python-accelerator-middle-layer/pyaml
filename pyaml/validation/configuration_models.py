"""Datamodels for configuration."""

import importlib
import logging
from typing import ClassVar

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class PyAMLBaseModel(BaseModel):
    """
    Base model for pyAML schemas.

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
    Base model for validating externally supplied configuration data.

    Each configuration schema defines the expected input for configuring a
    specific object and includes a ``class`` field containing its fully
    qualified class path.
    """

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True, arbitrary_types_allowed=False, extra="forbid")

    class_path: str = Field(
        description="Fully qualified class path.",
        alias="class",
    )


class ModuleConfigurationSchema(PyAMLBaseModel):
    """
    Base model for validating externally supplied configuration data.

    This schema exists to support legacy module-based configurations. It
    defines the expected input for configuring a specific object, with the
    target class resolved from the module's ``PYAMLCLASS`` attribute.
    """

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True, extra="forbid")

    MODULE_PATH_ALIASES: ClassVar[tuple[str, ...]] = ("module", "type")

    module_path: str = Field(
        description="Fully qualified module path.",
        alias=AliasChoices(*MODULE_PATH_ALIASES),
    )

    def to_configuration(self) -> ConfigurationSchema:
        """
        Convert the module-based configuration to a ``ConfigurationSchema``.

        Imports the referenced module, resolves the target class from its
        ``PYAMLCLASS`` attribute, and returns an equivalent
        :class:`ConfigurationSchema`. Any additional configuration fields are
        preserved.

        Returns
        -------
        ConfigurationSchema
            Configuration schema with the resolved fully qualified class path.

        Raises
        ------
        ImportError
            If the referenced module cannot be imported.
        ValueError
            If the module does not define ``PYAMLCLASS``.
        """

        module = importlib.import_module(self.module_path)

        try:
            class_name = module.PYAMLCLASS
        except AttributeError as e:
            raise ValueError(f"Module '{self.module_path}' does not define PYAMLCLASS.") from e

        return ConfigurationSchema.model_validate(
            {
                "class_path": f"{self.module_path}.{class_name}",
                **(self.model_extra or {}),
            },
            extra="allow",
        )
