"""Module for generating JSON Schema from registered configuration schemas."""

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import core_schema

from .models import ConfigurationSchema
from .registry import SchemaRegistry

logger = logging.getLogger(__name__)


class SchemaGenerator:
    """
    Generate JSON Schemas for registered configuration models.

    This class provides convenience methods for generating and exporting
    JSON Schemas from models registered in the ``SchemaRegistry``. Schema
    generation is delegated to a custom Pydantic JSON Schema generator
    that adds support for registry-aware polymorphism.

    Configuration base classes with registered subclasses are represented
    as ``oneOf`` unions over their concrete implementations, allowing
    generated schemas to describe all valid registered configuration types.

    Primitive unions such as ``str | None`` are emitted using compact
    ``type: [...]`` representations when supported by Pydantic.
    """

    _registry = SchemaRegistry()

    @classmethod
    def save(
        cls,
        class_path: str,
        filename: str | Path,
        *,
        indent: int = 2,
    ) -> Path:
        """
        Generate JSON Schema and save it to a file.

        Parameters
        ----------
        class_path : str
            Registered class path to generate schema for.
        filename : str or Path
            Output filename.
        indent : int, optional
            JSON indentation level. Default: 2.

        Returns
        -------
        Path
            Path to the written file.
        """
        schema = cls.generate(class_path)

        path = Path(filename)

        with path.open("w", encoding="utf-8") as file:
            json.dump(schema, file, indent=indent)

        return path

    @classmethod
    def generate(cls, class_path: str) -> dict[str, Any]:
        """
        Generate a JSON Schema for a registered configuration schema.

        The schema is generated using a custom Pydantic JSON Schema generator
        that expands registered configuration subclasses into ``oneOf`` unions
        and preserves compact representations for primitive unions such as
        ``str | None``.

        Parameters
        ----------
        class_path : str
            Registry key identifying the configuration schema class.

        Returns
        -------
        dict[str, Any]
            Generated JSON Schema for the requested configuration schema.

        Raises
        ------
        KeyError
            If no schema is registered for the given class path.
        """

        schema_cls = cls._registry.get(class_path)

        logger.debug("Generating schema for %s.", schema_cls)

        if schema_cls is None:
            raise KeyError(f"No schema registered for '{class_path}'")

        return schema_cls.model_json_schema(
            union_format="primitive_type_array",
            schema_generator=RegistryJsonSchema,
        )


METADATA_KEYS = (
    "title",
    "description",
    "examples",
    "deprecated",
    "readOnly",
    "writeOnly",
)


class RegistryJsonSchema(GenerateJsonSchema):
    """
    Custom Pydantic JSON Schema generator for configuration schemas.

    This generator extends the default Pydantic schema generation to support
    registry-aware polymorphism for ``ConfigurationSchema`` subclasses.

    For configuration base classes with registered subclasses, the generated
    schema is replaced by a ``oneOf`` union over all registered concrete
    subclasses. Human-facing schema metadata such as titles and descriptions
    are preserved from the original schema.

    In addition, all generated schema unions are normalized to use ``oneOf``
    instead of ``anyOf`` for improved compatibility with downstream tooling.
    Primitive unions such as ``str | None`` continue to use compact
    ``type: [...]`` representations when supported by Pydantic.
    """

    _registry = SchemaRegistry()

    def model_schema(self, schema: core_schema.ModelSchema) -> dict[str, Any]:
        """
        Generate a JSON Schema for a Pydantic model.

        For ``ConfigurationSchema`` subclasses with registered concrete
        subclasses, the generated schema is replaced by a ``oneOf`` union
        over all registered subclasses. Metadata fields from the original
        schema, such as titles and descriptions, are preserved.

        Parameters
        ----------
        schema : core_schema.ModelSchema
            Pydantic core schema describing the model.

        Returns
        -------
        dict[str, Any]
            Generated JSON Schema for the model.
        """

        base_schema = super().model_schema(schema)
        model_cls = schema.get("cls")
        logging.debug(f"Base schema is extracted from {model_cls}.")

        if not isinstance(model_cls, type) or not issubclass(model_cls, ConfigurationSchema):
            return base_schema

        candidates = [
            schema_cls
            for _, schema_cls in self._registry.items()
            if (isinstance(schema_cls, type) and issubclass(schema_cls, model_cls) and schema_cls is not model_cls)
        ]

        logging.debug(f"Subclasses for found in registry: {candidates}.")

        if not candidates:
            return base_schema

        # Generate schemas of subclasses
        subschemas = [self.generate_inner(candidate.__pydantic_core_schema__) for candidate in candidates]

        merged: dict[str, Any] = {"oneOf": subschemas}

        for key in METADATA_KEYS:
            if key in base_schema and key not in merged:
                merged[key] = deepcopy(base_schema[key])

        return merged

    def get_union_of_schemas(self, schemas: list[JsonSchemaValue]) -> JsonSchemaValue:
        """
        Combine multiple JSON Schemas into a union schema.

        This override normalizes generated union schemas to use ``oneOf``
        instead of ``anyOf`` for improved downstream compatibility.

        Parameters
        ----------
        schemas : list[JsonSchemaValue]
            JSON Schemas to combine into a union.

        Returns
        -------
        JsonSchemaValue
            Combined union schema.
        """

        schema = super().get_union_of_schemas(schemas)
        logging.debug(f"Modifying union schema for {schema}.")

        if "anyOf" in schema:
            schema = deepcopy(schema)
            schema["oneOf"] = schema.pop("anyOf")

        return schema


# #        return cls._expand_registry_refs(schema, model_cls)

#     @classmethod
#     def _expand_registry_refs(
#         cls,
#         schema: dict[str, Any],
#         model_cls: type[ConfigurationSchema],
#     ) -> dict[str, Any]:
#         """
#         Replace nested configuration-model fields with registry-backed schemas.

#         The input schema is usually produced by Pydantic. This method walks the
#         model fields and replaces fields whose annotations contain configuration
#         models with expanded schemas built from the registry.
#         """
#         expanded = deepcopy(schema)

#         properties = expanded.get("properties")
#         if not isinstance(properties, dict):
#             return expanded

#         for field_name, field_info in model_cls.model_fields.items():
#             if field_name not in properties:
#                 continue

#             replacement = cls._schema_for_annotation(field_info.annotation)
#             if replacement is None:
#                 continue

#             properties[field_name] = cls._merge_field_schema(
#                 base_schema=properties[field_name],
#                 replacement_schema=replacement,
#             )

#         return expanded

#     @classmethod
#     def _schema_for_annotation(cls, annotation: Any) -> dict[str, Any] | None:
#         """
#         Build a replacement JSON Schema for an annotation only when it contains
#         a configuration model that should be expanded via the registry.

#         Returns None when the base Pydantic schema should be kept as-is.
#         """
#         annotation = cls._unwrap_annotated(annotation)
#         origin = get_origin(annotation)
#         args = get_args(annotation)

#         if cls._is_union(origin):
#             branch_schemas: list[dict[str, Any]] = []
#             changed = False

#             for arg in args:
#                 if arg is NoneType:
#                     branch_schemas.append({"type": "null"})
#                     changed = True
#                     continue

#                 branch_schema = cls._schema_for_annotation(arg)
#                 if branch_schema is None:
#                     branch_schema = TypeAdapter(arg).json_schema(
#                         ref_template="#/$defs/{model}",
#                     )
#                 else:
#                     changed = True

#                 branch_schemas.append(branch_schema)

#             return {"anyOf": branch_schemas} if changed else None

#         if origin in (list, tuple):
#             item_annotation = args[0] if args else Any
#             item_schema = cls._schema_for_annotation(item_annotation)

#             if item_schema is None:
#                 return None

#             return {
#                 "type": "array",
#                 "items": item_schema,
#             }

#         if origin is dict:
#             value_annotation = args[1] if len(args) > 1 else Any
#             value_schema = cls._schema_for_annotation(value_annotation)

#             if value_schema is None:
#                 return None

#             return {
#                 "type": "object",
#                 "additionalProperties": value_schema,
#             }

#         if cls._is_configuration_model(annotation):
#             return cls._schema_for_configuration_model(annotation)

#         return None

#     @classmethod
#     def _schema_for_configuration_model(
#         cls,
#         base_model_cls: type[ConfigurationSchema],
#     ) -> dict[str, Any]:
#         """
#         Return a schema for one configuration model type.

#         If the registry contains concrete subclasses of the base model, return a
#         oneOf schema over those subclasses. Otherwise, fall back to the model's
#         own JSON Schema.
#         """
#         candidates = cls._concrete_registered_subclasses(base_model_cls)

#         if not candidates:
#             return base_model_cls.model_json_schema(ref_template="#/$defs/{model}")

#         if len(candidates) == 1:
#             return cls._generate_schema_for_model(candidates[0])

#         return {
#             "oneOf": [
#                 cls._generate_schema_for_model(schema_cls)
#                 for schema_cls in candidates
#             ]
#         }

#     @classmethod
#     def _concrete_registered_subclasses(
#         cls,
#         base_model_cls: type[ConfigurationSchema],
#     ) -> list[type[ConfigurationSchema]]:
#         """Return all registered schemas that inherit from the given base model."""
#         candidates: list[type[ConfigurationSchema]] = []

#         for _, schema_cls in cls._registry.items():
#             if (
#                 isinstance(schema_cls, type)
#                 and issubclass(schema_cls, base_model_cls)
#                 and schema_cls is not base_model_cls
#             ):
#                 candidates.append(schema_cls)

#         return candidates

#     @classmethod
#     def _merge_field_schema(
#         cls,
#         base_schema: dict[str, Any],
#         replacement_schema: dict[str, Any],
#     ) -> dict[str, Any]:
#         """
#         Preserve human-facing metadata from the original Pydantic field schema
#         while replacing the structural part with our registry-expanded schema.
#         """
#         merged = deepcopy(replacement_schema)

#         for key in (
#             "title",
#             "description",
#             "default",
#             "examples",
#             "deprecated",
#             "readOnly",
#             "writeOnly",
#         ):
#             if key in base_schema and key not in merged:
#                 merged[key] = deepcopy(base_schema[key])

#         return merged

#     @classmethod
#     def _is_configuration_model(cls, annotation: Any) -> bool:
#         """Check whether an annotation is a configuration model class."""
#         return (
#             isinstance(annotation, type)
#             and issubclass(annotation, ConfigurationSchema)
#         )

#     @classmethod
#     def _is_union(cls, origin: Any) -> bool:
#         """Check whether an annotation origin represents a union."""
#         return origin in (Union, UnionType)

#     @classmethod
#     def _unwrap_annotated(cls, annotation: Any) -> Any:
#         """Strip typing.Annotated[...] wrappers."""
#         origin = get_origin(annotation)
#         if origin is Annotated:
#             return get_args(annotation)[0]
#         return annotation
