"""Base datamodels for configuration."""

import inspect
import logging
from typing import Any, get_type_hints

from pydantic import BaseModel, ConfigDict, Field, create_model

logger = logging.getLogger(__name__)


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

    Provides common fields and functionality for schemas which are to be registered in the :class:`SchemaRegistry`.
    """

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True, arbitrary_types_allowed=False, extra="forbid")

    class_path: str = Field(
        description="Fully qualified class path.",
        alias="class",
    )


class ValidationSchema(PyAMLBaseModel):
    """
    Base model for validation schemas.

    Provides common fields and functionality for schemas used to validate arguments during object creation.
    """

    model_config = ConfigDict(arbitrary_types_allowed=False, extra="forbid")


class ValidationMeta(type):
    """
    Metaclass that validates constructor arguments using a Pydantic model.

    Classes using this metaclass must define a ``validation_model``
    attribute containing a subclass of :class:`pydantic.BaseModel`.
    Before an instance is created, the supplied arguments are bound to
    the ``__init__`` signature and validated against the model.

    Both positional and keyword arguments are validated before
    ``__init__`` is executed.
    """

    def __call__(cls, *args: Any, **kwargs: Any):
        """
        Create an instance after validating constructor arguments.

        The supplied arguments are bound to the class ``__init__`` signature,
        default values are applied, and the resulting argument mapping is
        validated using ``validation_model``. The validated values are then
        passed to the constructor.

        Raises
        ------
        TypeError
            If the class does not define ``validation_model``.

        ValidationError
            If the supplied arguments do not conform to the validation
            model.
        """

        validation_model = getattr(cls, "validation_model", None)

        if validation_model is None:
            raise TypeError(f"{cls.__name__} must define validation_model.")

        # Inspect the signature of the class
        signature = inspect.signature(cls.__init__)

        # Map arguments to parameters
        bound = signature.bind(None, *args, **kwargs)

        # Include default arguments
        bound.apply_defaults()

        # Remove self from list
        bound.arguments.pop("self", None)
        arguments = dict(bound.arguments)

        # Validate the model
        logger.debug("Validating input against schema: %s", validation_model.model_fields)
        validated = validation_model.model_validate(arguments)

        # Return the object
        return super().__call__(**validated.model_dump())


class DynamicValidation(metaclass=ValidationMeta):
    """
    Base class that generates a validation schema from the constructor
    signature.

    When a subclass is defined, a schema derived from
    :class:`ValidationSchema` is generated automatically and assigned to
    ``validation_model``. The generated schema is used by
    :class:`ValidationMeta` to validate constructor arguments before
    instance creation.

    Subclasses must not define ``validation_model`` manually.
    """

    validation_model: type[ValidationSchema] | None = None

    def __init_subclass__(cls, **kwargs):
        """
        Generate and attach a validation schema for the subclass.

        A schema derived from :class:`ValidationSchema` is created from the
        subclass's ``__init__`` signature and assigned to
        ``validation_model``. Defining ``validation_model`` explicitly is
        not permitted and results in a :class:`TypeError`.
        """

        super().__init_subclass__(**kwargs)

        if getattr(cls, "validation_model", None) is not None:
            raise TypeError(f"{cls.__name__} may not define validation_model manually.")

        cls.validation_model = cls._build_validation_model()

    @classmethod
    def _build_validation_model(cls) -> type[ValidationSchema]:
        """
        Build a validation schema from the constructor signature.

        The generated schema contains one field for each parameter in the
        subclass's ``__init__`` method, excluding ``self``, ``*args`` and
        ``**kwargs``. Field types are obtained from the constructor's type
        annotations and default values are preserved.

        Returns
        -------
        type[ValidationSchema]
            A dynamically generated subclass of :class:`ValidationSchema`
            representing the constructor arguments accepted by the subclass.
        """

        logger.debug("Building validation schema for %s.", f"{cls.__module__}.{cls.__name__}")

        signature = inspect.signature(cls.__init__)
        type_hints = get_type_hints(cls.__init__)

        fields: dict[str, tuple[Any, Any]] = {}

        # Skip *args and **kwargs
        for name, param in signature.parameters.items():
            if name == "self":
                continue

            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            annotation = type_hints.get(name, Any)
            default = param.default if param.default is not inspect._empty else ...
            fields[name] = (annotation, default)

        model = create_model(f"{cls.__name__}ValidationSchema", **fields, __base__=ValidationSchema)

        logger.debug("Created model: %s", model.model_fields)

        return model


class StaticValidation(metaclass=ValidationMeta):
    """
    Base class for explicit constructor validation.

    Subclasses must define a ``validation_model`` attribute containing a
    subclass of :class:`pydantic.BaseModel`. The model is used by
    :class:`ValidationMeta` to validate constructor arguments before
    instance creation.
    """

    validation_model: type[BaseModel]

    def __init_subclass__(cls, **kwargs):
        """
        Verify that the subclass defines a validation model.

        Raises
        ------
        TypeError
            If the subclass does not define a ``validation_model``
            attribute.
        """

        super().__init_subclass__(**kwargs)

        if getattr(cls, "validation_model", None) is None:
            raise TypeError(f"{cls.__name__} must define validation_model.")
