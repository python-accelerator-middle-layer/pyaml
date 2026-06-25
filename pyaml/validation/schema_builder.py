"""Functionality for dynamically generating configuration schemas."""

import inspect
import types
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from functools import reduce
from pathlib import Path
from typing import Annotated, Any, Literal, Union, get_args, get_origin, get_type_hints
from uuid import UUID

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from .configuration_models import ConfigurationSchema
from .registry import SchemaRegistry

RESERVED_CONFIGURATION_FIELDS = {"class_path"}

SUPPORTED_TYPES = (
    int,
    str,
    float,
    bool,
    bytes,
    dict,
    list,
    tuple,
    set,
    frozenset,
    type(None),
    datetime,
    date,
    time,
    timedelta,
    Decimal,
    Path,
    UUID,
)


def generate_configuration_schema(source: type) -> type[ConfigurationSchema]:
    """
    Generate a configuration schema for a class or Pydantic model.

    If the source defines a ``validation_model`` attribute containing a
    Pydantic model, the configuration schema is generated from that model.
    Otherwise, the schema is generated from the source class constructor
    signature.

    Generated schemas are registered in the :class:`SchemaRegistry` and
    reused on subsequent requests.
    """

    if not isinstance(source, type):
        raise TypeError("Source must be a class.")

    registry = SchemaRegistry()
    class_path = f"{source.__module__}.{source.__name__}"

    existing = registry.get(class_path)
    if existing is not None:
        return existing

    # Check if the class has a validation model
    validation_model = getattr(source, "validation_model", None)

    if isinstance(validation_model, type) and issubclass(validation_model, BaseModel):
        schema = _configuration_schema_from_basemodel(
            validation_model,
            _generate_schema_name(source),
            source.__module__,
        )
    else:
        schema = _configuration_schema_from_constructor(source)

    registry.register(class_path, schema)

    return schema


def _generate_schema_name(source: type) -> str:
    """
    Generate the default configuration schema name for a source class.
    """
    return f"{source.__name__}ConfigurationSchema"


def _configuration_schema_from_basemodel(
    validation_model: type[BaseModel],
    schema_name: str,
    module_name: str,
) -> type[ConfigurationSchema]:
    """
    Generate a configuration schema from a Pydantic model.

    The resulting schema contains one field for each field defined on the
    validation model, with field metadata and defaults preserved.
    """

    if not isinstance(validation_model, type) or not issubclass(validation_model, BaseModel):
        raise TypeError("validation_model must be a subclass of pydantic.BaseModel.")

    fields: dict[str, tuple[object, object]] = {}

    for field_name, field_info in validation_model.model_fields.items():
        if field_name in RESERVED_CONFIGURATION_FIELDS:
            raise ValueError(
                f"{validation_model.__name__} defines reserved field {field_name!r}, which is owned by ConfigurationSchema."
            )

        fields[field_name] = _field_definition_from_field_info(field_name, field_info)

    return create_model(
        schema_name,
        __base__=ConfigurationSchema,
        __module__=module_name,
        **fields,
    )


def _field_definition_from_field_info(field_name: str, field_info: FieldInfo) -> tuple[object, object]:
    """
    Convert a Pydantic field definition into a ``create_model`` field tuple.
    """

    # Get the annotation
    annotation = _resolve_annotation(field_info.annotation)

    # Handle default
    default = field_info.default
    if default is PydanticUndefined:
        default = ...

    # Handle default factory
    default_factory = field_info.default_factory

    # Collect metadata
    field_kwargs = _field_kwargs(field_name, field_info)

    if default_factory is not None:
        return annotation, Field(default_factory=default_factory, **field_kwargs)
    elif field_kwargs:
        return annotation, Field(default, **field_kwargs)
    else:
        return annotation, default


def _resolve_annotation(annotation: object) -> object:
    """
    Resolve an annotation into a schema-friendly type.

    Supported annotations are passed through directly, while supported
    generic types are resolved recursively into equivalent type hints.
    """

    if annotation is inspect._empty:
        return Any

    if annotation is None:
        return type(None)

    if isinstance(annotation, str):
        raise TypeError(f"Unable to resolve annotation {annotation!r}. Forward references are not currently supported.")

    # Check if is a generic type
    origin = get_origin(annotation)

    # If not a generic type
    if origin is None:
        if isinstance(annotation, type):
            if annotation in SUPPORTED_TYPES:
                return annotation

            if issubclass(annotation, Enum):
                return annotation

            if issubclass(annotation, ConfigurationSchema):
                return annotation

            return generate_configuration_schema(annotation)

        raise TypeError(f"Unsupported annotation: {annotation!r}")

    # If is generic type
    args = get_args(annotation)

    if origin is Annotated:
        return Annotated[_resolve_annotation(args[0]), *args[1:]]  # type: ignore[index]

    elif origin is Literal:
        return annotation

    elif origin is list:
        return list[_resolve_annotation(args[0])]

    elif origin is dict:
        return dict[_resolve_annotation(args[0]), _resolve_annotation(args[1])]

    elif origin is tuple:
        # Handle variable length tuple
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple[_resolve_annotation(args[0]), ...]

        resolved_args = tuple(_resolve_annotation(arg) for arg in args)
        return tuple[resolved_args]

    elif origin is set:
        return set[_resolve_annotation(args[0])]

    elif origin is frozenset:
        return frozenset[_resolve_annotation(args[0])]

    elif origin is Union or origin is types.UnionType:
        resolved_args = tuple(_resolve_annotation(arg) for arg in args)
        return reduce(lambda a, b: a | b, resolved_args[1:], resolved_args[0])

    else:
        raise TypeError(f"Unsupported generic annotation: {annotation!r}")


def _field_kwargs(field_name: str, field_info: object) -> dict[str, object]:
    """
    Collect supported field metadata for ``pydantic.create_model``.
    """

    kwargs: dict[str, object] = {}

    description = getattr(field_info, "description", None)
    if description is not None:
        kwargs["description"] = description

    title = getattr(field_info, "title", None)
    if title is not None:
        kwargs["title"] = title

    examples = getattr(field_info, "examples", None)
    if examples:
        kwargs["examples"] = examples

    deprecated = getattr(field_info, "deprecated", None)
    if deprecated is not None:
        kwargs["deprecated"] = deprecated

    alias = getattr(field_info, "alias", None)
    if alias and alias != field_name:
        kwargs["alias"] = alias

    return kwargs


def _configuration_schema_from_constructor(cls: type) -> type[ConfigurationSchema]:
    """
    Generate a configuration schema from a class constructor signature.

    The resulting schema contains one field for each constructor parameter,
    with annotations and default values preserved.
    """

    if not isinstance(cls, type):
        raise TypeError("cls must be a class.")

    fields = _fields_from_constructor_signature(
        cls,
        expand_arbitrary_types=True,
    )

    return create_model(
        _generate_schema_name(cls),
        __base__=ConfigurationSchema,
        __module__=cls.__module__,
        **fields,
    )


def _fields_from_constructor_signature(cls: type, expand_arbitrary_types: bool = False) -> dict[str, tuple[object, object]]:
    """
    Extract field definitions from a class constructor signature.

    Parameters
    ----------
    cls
        Class whose ``__init__`` method should be inspected.
    expand_arbitrary_types
        If true, unsupported annotations are expanded recursively into
        schema-friendly types.
    """

    signature = inspect.signature(cls.__init__)
    type_hints = get_type_hints(cls.__init__, include_extras=True)

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

        if name in RESERVED_CONFIGURATION_FIELDS:
            raise ValueError(
                f"{cls.__name__}.__init__ defines reserved parameter {name!r}, which is owned by ConfigurationSchema."
            )

        annotation = type_hints.get(name, Any)

        if expand_arbitrary_types:
            annotation = _resolve_annotation(annotation)

        default = param.default if param.default is not inspect._empty else ...
        fields[name] = (annotation, default)

    return fields
