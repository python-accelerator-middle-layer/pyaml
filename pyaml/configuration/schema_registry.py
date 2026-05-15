from __future__ import annotations

import importlib
import logging
import pkgutil
import warnings
from typing import Any, Callable, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .configuration_models import (
    ConfigurationSchema,
    ModuleConfigurationSchema,
)
from .legacy_handler import discover_legacy_schemas

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """
    Registry for dynamically registered schemas.
    """

    _instance: "SchemaRegistry | None" = None

    # Schemas as registered as class_path -> schema
    _schemas: dict[str, Type[BaseModel]]

    def __new__(cls) -> "SchemaRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._schemas = {}
        return cls._instance

    # ==========================================================
    # Registration
    # ==========================================================

    def register(
        self,
        class_path: str,
        schema: Type[ConfigurationSchema],
    ) -> None:
        if not issubclass(
            schema,
            ConfigurationSchema,
        ):
            raise TypeError(f"{schema.__name__} must inherit from ClassConfigurationSchema.")

        # TODO: handle this so no error if already registered the same.
        if class_path in self._schemas:
            raise ValueError(f"{class_path} already registered.")

        self._schemas[class_path] = schema

    def discover(self) -> None:
        root_package = __package__.split(".")[0]

        package = importlib.import_module(root_package)

        for _, module_name, _ in pkgutil.walk_packages(
            package.__path__,
            package.__name__ + ".",
        ):
            importlib.import_module(module_name)

        discover_legacy_schemas(self)

    # ==========================================================
    # Interaction
    # ==========================================================

    def __getitem__(
        self,
        class_path: str,
    ) -> Type[BaseModel]:
        try:
            return self._schemas[class_path]

        except KeyError:
            raise KeyError(f"No schema registered for '{class_path}'") from None

    def __contains__(
        self,
        class_path: str,
    ) -> bool:
        return class_path in self._schemas

    # ==========================================================
    # Validation
    # ==========================================================

    def validate(self, data: dict[str, Any]) -> BaseModel:
        """
        Recursively validate nested configuration.
        """

        validated = self._recursive_validate(data)

        if not isinstance(validated, BaseModel):
            raise TypeError("Top-level config did not validate to BaseModel.")

        return validated

    def _recursive_validate(self, obj: Any) -> Any:
        # List
        if isinstance(obj, list):
            return [self._recursive_validate(item) for item in obj]

        # Dict
        if isinstance(obj, dict):
            logger.debug("Validating dict: %s", obj)
            # First recurse children
            validated_dict = {key: self._recursive_validate(value) for key, value in obj.items()}

            # Check if the dict contains keys for a new item
            # Try class-based config first
            try:
                config = ConfigurationSchema.model_validate(validated_dict, extra="allow")
            except ValidationError:
                logger.debug(
                    "Could not validate against ConfigurationSchema. Falling back to legacy ModuleConfigurationSchema."
                )
                # Fall back to legacy module-based config
                try:
                    module_config = ModuleConfigurationSchema.model_validate(validated_dict, extra="allow")
                except ValidationError:
                    logger.debug("Could not validate against ModuleConfigurationSchema. Dict: %s is returned.", obj)
                    # Dict is normal dict so return as is
                    return validated_dict

                config = module_config.to_configuration()
                logger.debug("Dict transformed from legacy config.")

            class_path = config.class_path

            if class_path not in self:
                warnings.warn(
                    f"Unknown schema for '{class_path}', leaving as raw dict.",
                    stacklevel=2,
                )
                return validated_dict
            #                raise KeyError(f"Unknown schema for '{class_path}'")

            schema = self[class_path]
            return schema.model_validate(validated_dict)

        return obj


ModelT = TypeVar(
    "ModelT",
    bound=BaseModel,
)

ClassT = TypeVar("ClassT")


def register_schema(
    schema: Type[ModelT],
) -> Callable[[Type[ClassT]], Type[ClassT]]:
    """
    Decorator that registers a runtime class
    with a Pydantic schema.

    Usage
    -----
    @register_schema(MySchema)
    class MyClass:
        ...
    """

    registry = SchemaRegistry()

    def decorator(
        cls: Type[ClassT],
    ) -> Type[ClassT]:
        class_path = f"{cls.__module__}.{cls.__name__}"

        registry.register(
            class_path=class_path,
            schema=schema,
        )

        return cls

    return decorator
