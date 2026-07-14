"""Classes for validation during object creation."""

import inspect
import logging
from abc import ABCMeta
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, ValidationError, create_model

from .configuration_models import PyAMLBaseModel
from .errors import raise_validation_error
from .schema_builder import generate_class_path,_fields_from_class_definition

logger = logging.getLogger(__name__)


class ValidationModel(PyAMLBaseModel):
    """
    Base model for validating object constructor arguments.

    Each validation model defines the expected input for constructing a
    specific object.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ValidationMeta(ABCMeta):
    """
    Metaclass that validates constructor arguments before object creation.

    Classes using this metaclass must define a ``validation_model``
    attribute containing a subclass of :class:`pydantic.BaseModel`.
    Whenever an instance is created, the supplied constructor arguments
    are validated against the model before the class constructor is
    invoked.

    Pass `validate=False` to skip validation for a single construction.
    """

    def __call__(cls, *args: Any, **kwargs: Any):
        """
        Create an instance after optionally validating constructor arguments.

        Parameters
        ----------
        *args : Any
            Positional constructor arguments.
        **kwargs : Any
            Keyword constructor arguments.
        validate : bool, optional
            If ``True`` (default), validate constructor arguments before
            instantiation. If ``False``, skip validation and pass the
            supplied arguments directly to the constructor.

        Returns
        -------
        object
            Instance of the class after validation and construction.

        Raises
        ------
        TypeError
            If the class does not define ``validation_model``.
        PyAMLConfigException
            If the supplied arguments do not conform to the validation
            model.
        """
        validate = kwargs.pop("validate", True)

        if not validate:
            return super().__call__(*args, **kwargs)

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

        try:
            validated = validation_model.model_validate(arguments)
        except ValidationError as exc:
            raise_validation_error(
                exc,
                class_path=generate_class_path(cls),
            )

        # Return the object
        return super().__call__(**validated.model_dump())


class DynamicValidation(metaclass=ValidationMeta):
    """Base class for automatic constructor argument validation.

    When a subclass is defined, a validation model is generated from either
    its explicitly declared constructor or its directly declared class
    annotations.

    Class annotations are used when no constructor has yet been defined. This
    supports classes decorated with ``@dataclass``, because their generated
    constructor is not available while ``__init_subclass__`` is running.

    Subclasses must not define ``validation_model`` manually.
    """

    validation_model: type[ValidationModel] | None = None

    def __init_subclass__(cls, **kwargs):
        """
        Generate and attach a validation model for the subclass.

        Parameters
        ----------
        **kwargs : Any
            Additional keyword arguments passed to ``super().__init_subclass__``.

        Raises
        ------
        TypeError
            If ``validation_model`` is defined manually on the subclass.
        """

        super().__init_subclass__(**kwargs)

        if "validation_model" in cls.__dict__:
            raise TypeError(f"{cls.__name__} may not define validation_model manually.")

        cls.validation_model = cls._build_validation_model()

    @classmethod
    def _build_validation_model(cls) -> type[ValidationModel]:
        """Generate a validation model from the class definition.

        For classes with an explicitly defined ``__init__``, fields are
        extracted from the constructor signature. Otherwise, fields are
        extracted from annotations declared directly on the class. The latter
        supports dataclasses before their generated constructor is available.

        Returns
        -------
        type[ValidationModel]
            Dynamically generated validation model representing the arguments
            accepted by the class.
        """

        logger.debug("Building validation model for %s.", f"{cls.__module__}.{cls.__name__}")

        fields: dict[str, Any] = _fields_from_class_definition(cls, expand_arbitrary_types=False)

        model = create_model(f"{cls.__name__}ValidationModel", **cast(Any, fields), __base__=ValidationModel)

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

        Parameters
        ----------
        **kwargs : Any
            Additional keyword arguments passed to ``super().__init_subclass__``.

        Raises
        ------
        TypeError
            If the subclass does not define a ``validation_model``
            attribute.
        """

        super().__init_subclass__(**kwargs)

        if getattr(cls, "validation_model", None) is None:
            raise TypeError(f"{cls.__name__} must define validation_model.")
