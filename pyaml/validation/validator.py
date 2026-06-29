"""Module for schema validation."""

import logging
import warnings
from typing import Any

from pydantic import ValidationError

from .configuration_models import ConfigurationSchema, ModuleConfigurationSchema
from .errors import extract_location_metadata, raise_validation_error
from .registry import SchemaRegistry

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Recursive validator for configuration dictionaries.

    The validator traverses nested configuration data structures and
    converts dictionaries representing configuration objects into
    validated Pydantic schema models.

    Validation is performed recursively:

    - Lists are traversed element-by-element
    - Dictionaries are recursively validated
    - Dictionaries matching configuration schemas are converted into
      validated schema models
    - Dictionaries with unknown schemas are left unchanged

    Schema lookup is performed through the :class:`SchemaRegistry`.
    """

    _registry = SchemaRegistry()

    @classmethod
    def validate(
        cls,
        data: dict[str, Any],
    ) -> ConfigurationSchema:
        """Validate configuration data recursively.

        Parameters
        ----------
        data : dict[str, Any]
            Configuration dictionary to validate.

        Returns
        -------
        ConfigurationSchema
            Fully validated top-level configuration model.

        Raises
        ------
        TypeError
            If the validated top-level object is not a
            :class:`ConfigurationSchema`.
        """
        validated = cls._recursive_validate(data)

        # if not isinstance(validated, ConfigurationSchema):
        #     raise TypeError("Top-level configuration did not validate to a ConfigurationSchema.")

        return validated

    @classmethod
    def validate_to_dict(
        cls,
        data: dict[str, Any],
    ) -> dict:
        """
        Validate configuration data recursively and return it as a dictionary.
        """

        validated = cls.validate(data)
        if isinstance(validated, dict):
            return validated
        return validated.model_dump()

    @classmethod
    def _recursive_validate(cls, obj: Any) -> Any:
        """Recursively validate nested configuration objects.

        Lists are traversed recursively element-by-element. Dictionaries
        are recursively traversed and then interpreted as configuration
        objects when possible.

        If a dictionary corresponds to a registered configuration schema,
        it is converted into a validated schema model. Otherwise, the
        dictionary is returned unchanged.

        Parameters
        ----------
        obj : Any
            Object to validate recursively.

        Returns
        -------
        Any
            Validated object. This may be:

            - A validated configuration model
            - A recursively validated list
            - A recursively validated dictionary
            - The original object if no validation applies
        """
        if isinstance(obj, list):
            return [cls._recursive_validate(item) for item in obj]

        if not isinstance(obj, dict):
            return obj

        # Remove loader metadata and keep it for error reporting.
        cleaned_dict, location_metadata = extract_location_metadata(obj)

        logger.debug("Validating dict with keys: %s", list(obj))
        validated_dict = {key: cls._recursive_validate(value) for key, value in cleaned_dict.items()}

        # Check if the dict is a configuration object
        # If it follows the old convention for configuration
        # translate the data to the new one
        parsed = cls._parse_configuration(validated_dict)

        if parsed is None:
            return validated_dict
        else:
            validated_dict = parsed

        class_path = validated_dict["class_path"]
        schema = cls._registry.get(class_path)

        if schema is None:
            warnings.warn(
                f"Unknown schema for '{class_path}' so cannot validate. Leaving data as raw dict.",
                stacklevel=2,
            )
            return validated_dict

        try:
            return schema.model_validate(validated_dict)
        except ValidationError as exc:
            raise_validation_error(
                exc,
                class_path=class_path,
                location_metadata=location_metadata,
            )

    @classmethod
    def _parse_configuration(
        cls,
        validated_dict: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Interpret a dictionary as configuration metadata.

        Returns the dictionary unchanged if it already matches
        :class:`ConfigurationSchema`. If it matches
        :class:`ModuleConfigurationSchema`, the legacy module-based format is
        rewritten into the modern ``class_path`` form. Otherwise returns
        ``None``.
        """

        try:
            ConfigurationSchema.model_validate(validated_dict, extra="allow")
            return validated_dict
        except ValidationError:
            logger.debug("Could not validate against ConfigurationSchema.")

        try:
            module_config = ModuleConfigurationSchema.model_validate(
                validated_dict,
                extra="allow",
            )
        except ValidationError:
            logger.debug("Could not validate against ModuleConfigurationSchema; returning raw dict.")
            return None

        class_config = module_config.to_configuration()

        rewritten = dict(validated_dict)
        rewritten["class_path"] = class_config.class_path
        rewritten.pop("type", None)
        rewritten.pop("module", None)

        logger.debug("Configuration transformed from legacy configuration format.")
        return rewritten
