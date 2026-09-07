"""Datamodels for configuration."""

import importlib
import logging
from typing import Any, ClassVar

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

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

    @classmethod
    def describe(cls) -> str:
        """Return a readable description of the model fields."""
        lines = [f"{cls.__name__}("]

        for name, field in cls.model_fields.items():
            line = f"    {name}: {getattr(field.annotation, '__name__', field.annotation)}"
            if field.description:
                line += f" — {field.description}"
            lines.append(line)

        lines.append(")")
        return "\n".join(lines)


class ConfigurationSchema(PyAMLBaseModel):
    """
    Base model for configuration schemas.

    Each configuration schema defines the expected input for constructing a
    specific object. The required ``class`` field specifies the fully
    qualified class path of the object to construct.

    Notes
    -----
    Virtual subclasses may be registered to allow compatible schema types to
    be accepted during validation.
    """

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True, arbitrary_types_allowed=False, extra="forbid")

    class_path: str = Field(
        description="Fully qualified class path.",
        alias="class",
    )

    # Add implementation which mimics required behaviour of virtual subclasses
    # Real virtual subclasses are not compatible with Pydantic

    _virtual_subclasses: ClassVar[set[type["ConfigurationSchema"]]]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._virtual_subclasses = set()

    @classmethod
    def virtual_subclasses(cls) -> set[type["ConfigurationSchema"]]:
        """
        Return the registered virtual subclasses.

        Returns
        -------
        set[type[ConfigurationSchema]]
            A copy of the set containing all virtual subclasses registered
            for this schema class.
        """
        return set(cls._virtual_subclasses)

    @classmethod
    def register_virtual_subclass(cls, subclass: type["ConfigurationSchema"]) -> None:
        """
        Register a virtual subclass.

        Parameters
        ----------
        subclass : type[ConfigurationSchema]
            Subclass to register as a virtual subclass of this schema.

        Raises
        ------
        TypeError
            If ``subclass`` is not a ``ConfigurationSchema`` subclass.
        """

        if not isinstance(subclass, type) or not issubclass(subclass, ConfigurationSchema):
            raise TypeError(
                f"Cannot register {subclass!r} as a virtual subclass of {cls.__name__}: "
                "it is not a ConfigurationSchema subclass."
            )

        cls._virtual_subclasses.add(subclass)

    @classmethod
    def is_virtual_subclass_of(cls, superclass: type["ConfigurationSchema"]) -> bool:
        """
        Check whether this class is a subclass of another schema.

        Parameters
        ----------
        superclass : type[ConfigurationSchema]
            Schema class to compare against.

        Returns
        -------
        bool
            ``True`` if ``cls`` is ``superclass`` or a registered virtual
            subclass of it, otherwise ``False``.

        Raises
        ------
        TypeError
            If ``superclass`` is not a ``ConfigurationSchema`` subclass.
        """

        if not isinstance(superclass, type) or not issubclass(superclass, ConfigurationSchema):
            raise TypeError(f"{superclass!r} is not a ConfigurationSchema.")

        checked: set[type["ConfigurationSchema"]] = set()

        def subclass_exists(current_cls: type["ConfigurationSchema"]) -> bool:
            if current_cls in checked:
                return False
            checked.add(current_cls)

            if current_cls is cls:
                return True

            for child in current_cls._virtual_subclasses:
                if subclass_exists(child):
                    return True

            return False

        return subclass_exists(superclass)

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        """
        Customize Pydantic core schema generation.

        Parameters
        ----------
        source : Any
            Source type passed by Pydantic during schema generation.
        handler : GetCoreSchemaHandler
            Pydantic schema handler used to generate the default schema.

        Returns
        -------
        CoreSchema
            Wrapped core schema that accepts registered virtual subclasses.
        """

        # Get the normal schema
        schema = handler(source)

        def validate(value, nxt):
            # Already the expected schema type
            if isinstance(value, cls):
                return value

            # A registered virtual subclass instance should also be accepted
            if isinstance(value, ConfigurationSchema) and type(value).is_virtual_subclass_of(cls):
                return value

            # Otherwise let Pydantic validate normally
            return nxt(value)

        return core_schema.no_info_wrap_validator_function(validate, schema)


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
        validation_alias=AliasChoices(*MODULE_PATH_ALIASES),
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
