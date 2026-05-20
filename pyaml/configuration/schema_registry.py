import importlib
import logging
import pkgutil
import warnings
from collections.abc import ItemsView, Iterator, KeysView, ValuesView
from typing import Any, Callable, Type, TypeVar

from pydantic import ValidationError

from .configuration_models import (
    ConfigurationSchema,
    ModuleConfigurationSchema,
)
from .legacy_handler import discover_legacy_schemas

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """
    Singleton registry for dynamically registered schemas.

    The registry is used to validate data and produce
    jsonschemas for dynamic nested models.
    """

    _instance: "SchemaRegistry | None" = None

    # Schemas are registered as class_path -> schema
    _schemas: dict[str, Type[ConfigurationSchema]]

    def __new__(cls) -> "SchemaRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._schemas = {}
        return cls._instance

    # ==========================================================
    # Lookup
    # ==========================================================

    def __getitem__(
        self,
        class_path: str,
    ) -> Type[ConfigurationSchema]:
        """Return the registered schema for a class path.

        Parameters
        ----------
        class_path : str
            Fully qualified class path.

        Returns
        -------
        Type[ConfigurationSchema]
            Registered schema class.

        Raises
        ------
        KeyError
            If no schema has been registered for ``class_path``.
        """

        try:
            return self._schemas[class_path]

        except KeyError:
            raise KeyError(f"No schema registered for '{class_path}.'") from None

    def get(
        self,
        class_path: str,
    ) -> type[ConfigurationSchema] | None:
        """Return the registered schema for a class path.

        Parameters
        ----------
        class_path : str
            Fully qualified class path.

        Returns
        -------
        type[ConfigurationSchema] | None
            Registered schema class, or ``None`` if no schema is
            registered for ``class_path``.
        """
        return self._schemas.get(class_path)

    # ==========================================================
    # Contents
    # ==========================================================

    def __contains__(
        self,
        class_path: str,
    ) -> bool:
        """Return whether a schema is registered for a class path.

        Parameters
        ----------
        class_path : str
            Fully qualified class path.

        Returns
        -------
        bool
            ``True`` if a schema is registered for ``class_path``,
            otherwise ``False``.
        """
        return class_path in self._schemas

    def items(
        self,
    ) -> ItemsView[str, Type[ConfigurationSchema]]:
        """Return a view of registered schema items.

        Returns
        -------
        ItemsView[str, Type[ConfigurationSchema]]
            View of registered ``(class_path, schema)`` pairs.
        """
        return self._schemas.items()

    def keys(
        self,
    ) -> KeysView[str]:
        """Return a view of registered class paths.

        Returns
        -------
        KeysView[str]
            View of registered class paths.
        """
        return self._schemas.keys()

    def values(
        self,
    ) -> ValuesView[Type[ConfigurationSchema]]:
        """Return a view of registered schemas.

        Returns
        -------
        ValuesView[Type[ConfigurationSchema]]
            View of registered schema classes.
        """
        return self._schemas.values()

    def __len__(
        self,
    ) -> int:
        """Return the number of registered schemas.

        Returns
        -------
        int
            Number of registered schemas.
        """
        return len(self._schemas)

    def __iter__(
        self,
    ) -> Iterator[str]:
        """Iterate over registered class paths.

        Returns
        -------
        Iterator[str]
            Iterator over registered class paths.
        """
        return iter(self._schemas)

    # ==========================================================
    # Updating
    # ==========================================================

    def update(
        self,
        class_path: str,
        schema: type[ConfigurationSchema],
    ) -> None:
        """Replace the schema registered for a class path.

        Parameters
        ----------
        class_path : str
            Fully qualified class path.
        schema : type[ConfigurationSchema]
            Schema class used for validation. Must inherit from
            :class:`ConfigurationSchema`.

        Raises
        ------
        TypeError
            If ``schema`` is not a subclass of
            :class:`ConfigurationSchema`.
        KeyError
            If no schema has been registered for ``class_path``.
        """
        if not isinstance(schema, type) or not issubclass(schema, ConfigurationSchema):
            raise TypeError(f"{schema!r} must inherit from ConfigurationSchema.")

        if class_path not in self._schemas:
            raise KeyError(f"{class_path} is not registered.")

        self._schemas[class_path] = schema

    # ==========================================================
    # Registration
    # ==========================================================

    def register(
        self,
        class_path: str,
        schema: type[ConfigurationSchema],
    ) -> None:
        """Register a schema for a class path.

        Parameters
        ----------
        class_path : str
            Fully qualified class path.
        schema : type[ConfigurationSchema]
            Schema class used for validation. Must inherit from
            :class:`ConfigurationSchema`.

        Raises
        ------
        TypeError
            If ``schema`` is not a subclass of
            :class:`ConfigurationSchema`.
        ValueError
            If a different schema has already been registered for
            ``class_path``.
        """
        existing = self._schemas.get(class_path)
        if existing is not None and existing is not schema:
            raise ValueError(f"{class_path} already registered with a different schema.")

        if not isinstance(schema, type) or not issubclass(schema, ConfigurationSchema):
            raise TypeError(f"{schema!r} must inherit from ConfigurationSchema.")

        self._schemas[class_path] = schema

    def discover(self) -> None:
        """Discover and register schemas.

        This imports modules in the package so classes decorated with
        :func:`register_schema` are registered, then registers legacy
        schemas from ``pyproject.toml``.
        """

        # Import package modules so schema registration runs.
        root_package = __package__.split(".")[0]
        package = importlib.import_module(root_package)
        for _, module_name, _ in pkgutil.walk_packages(
            package.__path__,
            package.__name__ + ".",
        ):
            importlib.import_module(module_name)

        # Register legacy schemas defined in ``pyproject.toml``.
        discover_legacy_schemas(self)

        # TODO: Register schemas from external packages using entry points.

    def unregister(
        self,
        class_path: str,
    ) -> None:
        """Unregister a schema.

        Parameters
        ----------
        class_path : str
            Fully qualified class path.

        Raises
        ------
        KeyError
            If no schema has been registered for ``class_path``.
        """
        try:
            del self._schemas[class_path]

        except KeyError:
            raise KeyError(f"No schema registered for '{class_path}'") from None

    def clear(self) -> None:
        """Remove all registered schemas.

        This clears the registry in place.
        """
        self._schemas.clear()

    def __repr__(
        self,
    ) -> str:
        """Return a string representation of the registry."""
        if not self._schemas:
            return f"{self.__class__.__name__}({{}})"

        lines = [f"{self.__class__.__name__}("]

        for class_path, schema in sorted(self._schemas.items()):
            lines.append(f"    {class_path!r}: {schema.__module__}.{schema.__name__},")

        lines.append(")")

        return "\n".join(lines)

    # ==========================================================
    # Validation
    # ==========================================================

    def validate(
        self,
        data: dict[str, Any],
    ) -> ConfigurationSchema:
        """Validate configuration data recursively.

        Parameters
        ----------
        data : dict[str, Any]
            Configuration data to validate.

        Returns
        -------
        ConfigurationSchema
            Fully validated top-level configuration model.

        Raises
        ------
        TypeError
            If the top-level validated result is not a
            :class:`ConfigurationSchema`.
        """
        validated = self._recursive_validate(data)

        if not isinstance(validated, ConfigurationSchema):
            raise TypeError("Top-level configuration did not validate to a ConfigurationSchema.")

        return validated

    def _recursive_validate(self, obj: Any) -> Any:
        """Recursively validate nested configuration objects.

        Lists are traversed element by element. Dictionaries are first
        traversed recursively, then interpreted as configuration data if
        possible.

        Parameters
        ----------
        obj : Any
            Object to validate.

        Returns
        -------
        Any
            Validated object, which may be a validated model, a list of
            validated items, or the original object if no validation applies.
        """
        if isinstance(obj, list):
            return [self._recursive_validate(item) for item in obj]

        if not isinstance(obj, dict):
            return obj

        logger.debug("Validating dict with keys: %s", list(obj))
        validated_dict = {key: self._recursive_validate(value) for key, value in obj.items()}

        config = self._parse_configuration(validated_dict)
        if config is None:
            return validated_dict

        class_path = config.class_path
        schema = self._schemas.get(class_path)

        if schema is None:
            warnings.warn(
                f"Unknown schema for '{class_path}', leaving as raw dict.",
                stacklevel=2,
            )
            return validated_dict

        return schema.model_validate(validated_dict)

    def _parse_configuration(
        self,
        validated_dict: dict[str, Any],
    ) -> ConfigurationSchema | None:
        """Parse a dictionary as configuration metadata.

        Tries the current configuration format first, then falls back to
        the legacy module-based format.

        Returns
        -------
        ConfigurationSchema | None
            Parsed configuration object, or ``None`` if the dictionary does
            not match either format.
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


# ==========================================================
# Decorator to register schemas
# ==========================================================

ModelT = TypeVar("ModelT", bound=ConfigurationSchema)
ClassT = TypeVar("ClassT")


def register_schema(
    schema: Type[ModelT],
) -> Callable[[Type[ClassT]], Type[ClassT]]:
    """Register a runtime class with a Pydantic schema.

    Parameters
    ----------
    schema : Type[ModelT]
        Schema class to register. Must inherit from
        :class:`ConfigurationSchema`.

    Returns
    -------
    Callable[[Type[ClassT]], Type[ClassT]]
        Decorator that registers the decorated class with ``schema``.

    Examples
    --------
    >>> @register_schema(MySchema)
    ... class MyClass:
    ...     pass
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
