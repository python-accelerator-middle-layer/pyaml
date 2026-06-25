"""Registry for schemas."""

import importlib
import logging
import pkgutil
from collections.abc import ItemsView, Iterator, KeysView, ValuesView
from typing import Callable, Type, TypeVar, overload

from .configuration_models import ConfigurationSchema

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """
    Singleton registry for dynamically registered schemas.

    The registry is used to validate data and produce
    jsonschemas for dynamic nested models.
    """

    _instance: "SchemaRegistry | None" = None
    _schemas: dict[str, Type[ConfigurationSchema]]

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
# Decorator to register schemas
# ==========================================================

ClassT = TypeVar("ClassT")


@overload
def register_schema(cls: type[ClassT]) -> type[ClassT]: ...


@overload
def register_schema(schema: type[ConfigurationSchema]) -> Callable[[type[ClassT]], type[ClassT]]: ...


@overload
def register_schema() -> Callable[[type[ClassT]], type[ClassT]]: ...


def register_schema(arg: type | None = None):
    """
    Register a configuration schema for a class.

    This decorator supports three forms:

    - ``@register_schema``: generate and register a configuration schema
      from the decorated class.
    - ``@register_schema()``: equivalent to ``@register_schema``.
    - ``@register_schema(MyConfigurationSchema)``: register an explicit
      :class:`ConfigurationSchema` subclass for the decorated class.

    Automatically generated schemas are created using
    :func:`generate_configuration_schema` and registered in the
    :class:`SchemaRegistry`.
    """

    from .schema_builder import generate_configuration_schema

    registry = SchemaRegistry()

    def _generate_and_register_schema(cls: type[ClassT]) -> type[ClassT]:
        generate_configuration_schema(cls)
        return cls

    # Used as: @register_schema(schema)
    # Explicit registration of schema
    if isinstance(arg, type) and issubclass(arg, ConfigurationSchema):
        schema = arg

        def decorator(cls: type[ClassT]) -> type[ClassT]:
            class_path = f"{cls.__module__}.{cls.__name__}"
            logger.debug("Register schema for %s.", class_path)
            registry.register(class_path=class_path, schema=schema)
            return cls

        return decorator

    # Used as: @register_schema()
    # Registration is done when generating the schema
    if arg is None:

        def decorator(cls: type[ClassT]) -> type[ClassT]:
            return _generate_and_register_schema(cls)

        return decorator

    # Used as: @register_schema
    # Registration is done when generating the schema
    if isinstance(arg, type):
        return _generate_and_register_schema(arg)

    raise TypeError("register_schema must be used as a decorator or decorator factory.")
