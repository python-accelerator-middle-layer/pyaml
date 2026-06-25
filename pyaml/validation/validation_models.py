"""Classes for validation during object creation."""

import inspect
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, create_model

from .configuration_models import PyAMLBaseModel
from .schema_builder import _fields_from_constructor_signature

logger = logging.getLogger(__name__)


class ValidationModel(PyAMLBaseModel):
    """
    Base model for validating object constructor arguments.

    Each validation model defines the expected input for constructing a
    specific object.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ValidationMeta(type):
    """
    Metaclass that validates constructor arguments before object creation.

    Classes using this metaclass must define a ``validation_model``
    attribute containing a subclass of :class:`pydantic.BaseModel`.
    Whenever an instance is created, the supplied constructor arguments
    are validated against the model before the class constructor is
    invoked.
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
    Base class for automatic constructor argument validation.

    When a subclass is defined, a validation model is generated
    automatically from its constructor signature and assigned to
    ``validation_model``. The generated model is then used to validate
    constructor arguments before object creation.

    Subclasses must not define ``validation_model`` manually.
    """

    validation_model: type[ValidationModel] | None = None

    def __init_subclass__(cls, **kwargs):
        """
        Generate and attach a validation model for the subclass.

        A validation model is generated from the subclass's constructor
        signature and assigned to ``validation_model``. Defining
        ``validation_model`` explicitly is not permitted and results in a
        :class:`TypeError`.
        """

        super().__init_subclass__(**kwargs)

        if getattr(cls, "validation_model", None) is not None:
            raise TypeError(f"{cls.__name__} may not define validation_model manually.")

        cls.validation_model = cls._build_validation_model()

    @classmethod
    def _build_validation_model(cls) -> type[ValidationModel]:
        """
        Generate a validation model from the constructor signature.

        The generated model contains one field for each parameter in the
        subclass's ``__init__`` method, excluding ``self``, ``*args``, and
        ``**kwargs``. Field types are obtained from the constructor's type
        annotations and default values are preserved.

        Returns
        -------
        type[ValidationModel]
            A dynamically generated subclass of :class:`ValidationModel`
            representing the constructor arguments accepted by the subclass.
        """

        logger.debug("Building validation model for %s.", f"{cls.__module__}.{cls.__name__}")

        fields = _fields_from_constructor_signature(cls, expand_arbitrary_types=False)

        model = create_model(f"{cls.__name__}ValidationModel", **fields, __base__=ValidationModel)

        logger.debug("Created model: %s", model.model_fields)

        return model


class StaticValidation(metaclass=ValidationMeta):
    """
    Base class for explicit constructor argument validation.

    Subclasses must define a ``validation_model`` attribute containing a
    subclass of :class:`pydantic.BaseModel`. The model is used to validate
    constructor arguments before object creation.
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
