"""Classes for validation during object creation."""

import inspect
import logging
from abc import ABCMeta
from typing import Any, ClassVar, cast

from pydantic import BaseModel, ConfigDict, ValidationError, create_model

from .configuration_models import PyAMLBaseModel
from .errors import raise_validation_error
from .schema_builder import _fields_from_constructor_signature, generate_class_path

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

    The signature reported by :func:`inspect.signature` for classes using this
    metaclass is that of their ``__init__``, not of :meth:`__call__`. The
    ``validate`` keyword is therefore not part of the reported signature.
    """

    @property
    def __signature__(cls) -> inspect.Signature | None:
        """
        Report the constructor signature of the class.

        Without this, :func:`inspect.signature` resolves to :meth:`__call__` and
        reports ``(*args, **kwargs)`` for every class using this metaclass, which
        hides the real parameters from ``help()``, Sphinx and other tooling.

        Returns
        -------
        inspect.Signature | None
            Signature of ``cls.__init__`` without ``self``, or ``None`` if it
            cannot be determined, in which case the default introspection applies.
        """
        # Classes relying on ``object.__init__`` take no argument, as reported by
        # ``inspect.signature`` for a class without a metaclass
        if cls.__init__ is object.__init__ and cls.__new__ is object.__new__:
            return inspect.Signature()

        try:
            signature = inspect.signature(cls.__init__)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return None

        # Drop ``self`` and the constructor return annotation
        parameters = list(signature.parameters.values())[1:]

        return signature.replace(parameters=parameters, return_annotation=inspect.Signature.empty)

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


class ValidationModelDescriptor:
    """Provide a lazily generated validation model on the class."""

    def __get__(
        self,
        instance: object | None,
        owner: type["DynamicValidation"],
    ) -> type[ValidationModel]:
        """
        Return the validation model associated with ``owner``.

        The model is generated on first access and cached on the owning class.
        Because this descriptor exposes class-level metadata, ``instance`` is
        not used.

        Parameters
        ----------
        instance : object | None
            Instance through which the descriptor was accessed, or ``None``
            when accessed on the class.
        owner : type[DynamicValidation]
            Class whose validation model is requested.

        Returns
        -------
        type[ValidationModel]
            The cached or newly generated validation model.
        """
        model = owner.__dict__.get("_validation_model")

        if model is None:
            model = owner._build_validation_model()
            owner._validation_model = model

        return model


class DynamicValidation(metaclass=ValidationMeta):
    """
    Base class for automatic constructor argument validation.

    When a subclass is defined, a validation model is generated from either
    its explicitly declared constructor or its directly declared class
    annotations.

    Class annotations are used when no constructor has yet been defined. This
    supports classes decorated with ``@dataclass``, because their generated
    constructor is not available while ``__init_subclass__`` is running.

    Subclasses must not define ``validation_model`` manually.
    """

    _validation_model: ClassVar[type[ValidationModel] | None] = None

    # Lazy construction of the validation class
    validation_model: ClassVar[ValidationModelDescriptor] = ValidationModelDescriptor()

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

        # Check if validation model already exists
        # This only checks for the current class and not parent classes
        if "validation_model" in cls.__dict__:
            raise TypeError(f"{cls.__name__} may not define validation_model manually.")

        # Set the _validation_model to None since should be built using lazy construction
        cls._validation_model = None

    @classmethod
    def _build_validation_model(cls) -> type[ValidationModel]:
        """
        Generate a validation model from the class definition.

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

        fields: dict[str, Any] = _fields_from_constructor_signature(cls, expand_arbitrary_types=False)

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
