"""Module for schema validation."""

import logging
import warnings
from typing import Any

from pydantic import ValidationError

from .models import ConfigurationSchema, ModuleConfigurationSchema
from .registry import SchemaRegistry

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Recursive validator for configuration dictionaries.

    The validator traverses nested configuration data structures and
    converts dictionaries representing configuration objects into
    validated Pydantic schema models.

    Validation is performed recursively:

    - lists are traversed element-by-element
    - dictionaries are recursively validated
    - dictionaries matching configuration schemas are converted into
      validated schema models
    - dictionaries with unknown schemas are left unchanged

    Schema lookup is performed through the global
    :class:`SchemaRegistry`.
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

        if not isinstance(validated, ConfigurationSchema):
            raise TypeError("Top-level configuration did not validate to a ConfigurationSchema.")

        return validated

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

            - a validated configuration model
            - a recursively validated list
            - a recursively validated dictionary
            - the original object if no validation applies
        """
        if isinstance(obj, list):
            return [cls._recursive_validate(item) for item in obj]

        if not isinstance(obj, dict):
            return obj

        logger.debug("Validating dict with keys: %s", list(obj))
        validated_dict = {key: cls._recursive_validate(value) for key, value in obj.items()}

        config = cls._parse_configuration(validated_dict)
        if config is None:
            return validated_dict

        class_path = config.class_path
        schema = cls._registry.get(class_path)

        if schema is None:
            warnings.warn(
                f"Unknown schema for '{class_path}', leaving as raw dict.",
                stacklevel=2,
            )
            return validated_dict

        return schema.model_validate(validated_dict)

    @classmethod
    def _parse_configuration(
        cls,
        validated_dict: dict[str, Any],
    ) -> ConfigurationSchema | None:
        """Parse a dictionary as configuration metadata.

        The dictionary is first validated against the current
        :class:`ConfigurationSchema` format. If validation fails,
        validation falls back to the legacy
        :class:`ModuleConfigurationSchema` format.

        Legacy module-based configurations are automatically converted
        into the current configuration representation.

        Parameters
        ----------
        validated_dict : dict[str, Any]
            Dictionary to interpret as configuration metadata.

        Returns
        -------
        ConfigurationSchema | None
            Parsed configuration model if validation succeeds,
            otherwise ``None``.
        """
        try:
            return ConfigurationSchema.model_validate(
                validated_dict,
                extra="allow",
            )
        except ValidationError:
            logger.debug("Could not validate against ConfigurationSchema; trying legacy ModuleConfigurationSchema.")

        try:
            module_config = ModuleConfigurationSchema.model_validate(
                validated_dict,
                extra="allow",
            )
        except ValidationError:
            logger.debug("Could not validate against ModuleConfigurationSchema; returning raw dict.")
            return None

        logger.debug("Dict transformed from legacy config.")
        return module_config.to_configuration()
