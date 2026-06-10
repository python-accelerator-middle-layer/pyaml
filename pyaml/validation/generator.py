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


METADATA_KEYS = (
    "title",
    "description",
    "examples",
    "deprecated",
    "readOnly",
    "writeOnly",
)

CLASS_ALIAS = "class"


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
            by_alias=True,
            union_format="primitive_type_array",
            schema_generator=RegistryJsonSchema,
        )

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

        For ``ConfigurationSchema`` subclasses, the generated schema may be
        transformed into a polymorphic schema based on the registered schema
        registry:

        - If the model defines a ``class`` field, all registered aliases
        corresponding to the model are added as allowed literal values.
        - If registered subclasses exist, the schema is replaced by an
        ``anyOf`` union containing the schemas of all registered subclasses.

        Metadata fields from the original schema, such as titles and
        descriptions, are preserved in the merged schema.

        Parameters
        ----------
        schema : core_schema.ModelSchema
            Pydantic core schema describing the model.

        Returns
        -------
        dict[str, Any]
            Generated JSON Schema for the model or polymorphic union schema.

        Notes
        -----
        The generated polymorphic schema uses ``anyOf`` instead of ``oneOf``
        because nested ``oneOf`` unions may lead to ambiguous validation in
        downstream JSON Schema tooling when subclass schemas contain nullable
        or overlapping branches.
        """

        base_schema = super().model_schema(schema)
        model_cls = schema.get("cls")
        logging.debug(f"Base schema is extracted from {model_cls}.")

        if not isinstance(model_cls, type) or not issubclass(model_cls, ConfigurationSchema):
            return base_schema

        # If the baseschema has a class field, add literal for all keys.
        properties = base_schema.get("properties")
        if isinstance(properties, dict) and CLASS_ALIAS in properties and isinstance(properties[CLASS_ALIAS], dict):
            logging.debug(f"Adding list of classes to: {model_cls}.")

            # Find keys that correspond to the same schema
            base_keys = sorted(key for key, schema_cls in self._registry.items() if schema_cls is model_cls)

            base_schema = deepcopy(base_schema)
            properties = base_schema["properties"]
            self._add_literals_to_class_path(properties[CLASS_ALIAS], base_keys)

        # Get subclasses in registry sorted by module name
        subclasses = sorted(
            {
                schema_cls
                for _, schema_cls in self._registry.items()
                if isinstance(schema_cls, type) and issubclass(schema_cls, model_cls) and schema_cls is not model_cls
            },
            key=lambda cls: f"{cls.__module__}.{cls.__name__}",
        )
        logging.debug(f"Subclasses found in registry: {subclasses}.")

        if not subclasses:
            return base_schema

        # Generate schemas of subclasses
        subschemas = [self.generate_inner(item.__pydantic_core_schema__) for item in subclasses]

        # TODO: get the schemas to work when using oneOf instead
        merged: dict[str, Any] = {"anyOf": subschemas}

        for key in METADATA_KEYS:
            if key in base_schema and key not in merged:
                merged[key] = deepcopy(base_schema[key])

        return merged

    @staticmethod
    def _add_literals_to_class_path(schema: dict[str, Any], literals: list[str]) -> None:
        """
        Add allowed literal values to a JSON Schema string field.

        The provided literals are merged with any existing ``enum`` values in
        the schema while preserving insertion order and removing duplicates.

        If the resulting set contains only a single value, the schema is
        simplified by replacing ``enum`` with ``const``.

        The schema is modified in place.

        Parameters
        ----------
        schema : dict[str, Any]
            JSON Schema fragment representing a string-like field.
        literals : list[str]
            Literal values to add to the schema.

        Notes
        -----
        Only schemas representing string values or existing enumerations are
        modified. Empty literal lists are ignored.
        """

        if not literals:
            return

        # Add registry keys as literals
        if schema.get("type") == "string" or "enum" in schema:
            existing = schema.get("enum", [])
            merged = list(dict.fromkeys([*existing, *literals]))
            schema["enum"] = merged

            # If only one value exists use const
            if len(merged) == 1:
                schema["const"] = merged[0]
                schema.pop("enum", None)

            return
