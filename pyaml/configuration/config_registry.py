import logging
from collections import defaultdict
from collections.abc import ItemsView, Iterator, KeysView, ValuesView
from copy import deepcopy
from dataclasses import dataclass, field
from pprint import pformat
from typing import Any

from .schema_registry import SchemaRegistry

logger = logging.getLogger(__name__)


class ConfigurationItem:
    """Mutable configuration object with optional schema validation.

    Nested dictionaries containing a ``class_path`` field are wrapped as
    :class:`ConfigurationItem` instances so validation and mutation logic
    propagate recursively through configuration trees.

    Plain dictionaries without ``class_path`` remain ordinary dictionaries,
    but their contents are still traversed recursively.

    Parameters
    ----------
    data : dict[str, Any]
        Configuration data.
    validate : bool, optional
        If ``True``, validate the configuration against the registered
        schema associated with its ``class_path`` field.
    """

    def __init__(
        self,
        data: dict[str, Any],
        *,
        validate: bool = True,
    ) -> None:
        object.__setattr__(self, "_data", {})
        object.__setattr__(self, "_validate_enabled", validate)

        for key, value in data.items():
            self._data[key] = self._wrap(value)

        if self._validate_enabled:
            self._validate()

    def _wrap(self, value: Any) -> Any:
        """Recursively wrap configuration values.

        Dictionaries containing a ``class_path`` field are converted into
        :class:`ConfigurationItem` instances. Other dictionaries remain
        plain dictionaries, but their contents are traversed recursively.

        Lists are traversed element by element.

        Parameters
        ----------
        value : Any
            Value to wrap.

        Returns
        -------
        Any
            Wrapped value.
        """

        if isinstance(value, dict):
            if "class_path" in value:
                return ConfigurationItem(value, validate=self._validate_enabled)
            return {key: self._wrap(item) for key, item in value.items()}

        if isinstance(value, dict):
            return ConfigurationItem(value, validate=self._validate_enabled)

        if isinstance(value, list):
            return [self._wrap(item) for item in value]
        return value

    def _unwrap(self, value: Any) -> Any:
        """Recursively convert wrapped values back to plain Python objects.

        Parameters
        ----------
        value : Any
            Value to unwrap.

        Returns
        -------
        Any
            Plain Python representation.
        """

        if isinstance(value, ConfigurationItem):
            return value.to_dict()

        if isinstance(value, list):
            return [self._unwrap(item) for item in value]

        if isinstance(value, dict):
            return {key: self._unwrap(item) for key, item in value.items()}
        return value

    def to_dict(self) -> dict[str, Any]:
        """Return the configuration as a plain dictionary.

        Returns
        -------
        dict[str, Any]
            Plain Python representation of the configuration.
        """

        return {key: self._unwrap(value) for key, value in self._data.items()}

    def _validate(self) -> None:
        """Validate the configuration against its registered schema.

        Validation is performed recursively using
        :class:`SchemaRegistry`.

        Raises
        ------
        KeyError
            If no schema is registered for the configuration
            ``class_path``.
        ValidationError
            If schema validation fails.
        """

        data = self.to_dict()

        class_path = data.get("class_path")
        if not isinstance(class_path, str):
            return

        schema_registry = SchemaRegistry()
        if class_path not in schema_registry:
            raise KeyError(f"No schema registered for class_path {class_path!r}.")

        schema_registry.validate(data)

    def __getitem__(self, key: str) -> Any:
        """Return a configuration value."""

        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Return a configuration value or a default value.

        Parameters
        ----------
        key : str
            Configuration field name.
        default : Any, optional
            Value returned if ``key`` does not exist.

        Returns
        -------
        Any
            Stored configuration value or ``default``.
        """

        return self._data.get(key, default)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a configuration value with optional validation.

        The update is rolled back automatically if validation fails.

        Parameters
        ----------
        key : str
            Configuration field name.
        value : Any
            Replacement value.

        Raises
        ------
        ValidationError
            If validation fails after the update.
        """

        if key == "name" and "name" in self._data and value != self._data["name"]:
            raise ValueError("The 'name' field is immutable. Rename the item through the Registry instead.")

        old_value = self._data.get(key)
        had_key = key in self._data

        self._data[key] = self._wrap(value)

        if not self._validate_enabled:
            return

        try:
            self._validate()
        except Exception:
            if had_key:
                self._data[key] = old_value
            else:
                del self._data[key]
            raise

    def __getattr__(self, key: str) -> Any:
        """Provide attribute-style access to configuration fields.

        Parameters
        ----------
        key : str
            Configuration field name.

        Returns
        -------
        Any
            Stored configuration value.

        Raises
        ------
        AttributeError
            If the field does not exist.
        """

        try:
            return self._data[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: Any) -> None:
        """Provide attribute-style assignment for configuration fields.

        Internal attributes beginning with ``_`` bypass the configuration
        update machinery and are stored directly on the instance.

        Parameters
        ----------
        key : str
            Attribute name.
        value : Any
            Attribute value.
        """

        if key.startswith("_"):
            object.__setattr__(self, key, value)
            return
        self.__setitem__(key, value)

    def __repr__(self) -> str:
        """Return a pretty string representation of the :class:`ConfigurationItem`."""
        return f"{self.__class__.__name__}(\n{pformat(self.to_dict(), indent=4)}\n)"


class Registry:
    """Dictionary-like registry for configuration items.

    Items are stored under explicit string keys and wrapped as
    :class:`ConfigurationItem` instances. The registry supports both
    dictionary-style and attribute-style access.

    Parameters
    ----------
    validate : bool, optional
        If ``True``, validate stored configuration items during creation
        and modification.
    """

    def __init__(self, *, validate: bool = True) -> None:
        self._items: dict[str, ConfigurationItem] = {}
        self._validate = validate

    def add(self, key: str, value: dict[str, Any]) -> None:
        """Add a configuration item to the registry.

        Parameters
        ----------
        key : str
            Registry key.
        value : dict[str, Any]
            Configuration data.

        Raises
        ------
        TypeError
            If ``key`` is not a string or ``value`` is not a dictionary.
        ValueError
            If ``key`` already exists in the registry.
        """

        if not isinstance(key, str):
            raise TypeError("Registry key must be a string.")

        if not isinstance(value, dict):
            raise TypeError("Configuration must be a dictionary.")

        if key in self._items:
            raise ValueError(f"Configuration '{key}' already exists.")

        logger.debug("Adding %s to registry", key)
        self._items[key] = ConfigurationItem(
            deepcopy(value),
            validate=self._validate,
        )

    def rename(self, old: str, new: str) -> None:
        """Rename a stored configuration item.

        The registry key and the internal ``name`` field are updated
        together to maintain consistency.

        Parameters
        ----------
        old : str
            Existing registry key.
        new : str
            New registry key.

        Raises
        ------
        KeyError
            If ``old`` does not exist.
        ValueError
            If ``new`` already exists.
        """

        if old not in self._items:
            raise KeyError(f"No configuration stored for {old!r}.")
        if new in self._items:
            raise ValueError(f"Configuration {new!r} already exists.")

        item = self._items.pop(old)
        item._data["name"] = new
        self._items[new] = item

    def __getitem__(self, key: str) -> ConfigurationItem:
        """Return a stored configuration item.

        Parameters
        ----------
        key : str
            Registry key.

        Returns
        -------
        ConfigurationItem
            Stored configuration item.
        """
        return self._items[key]

    def get(
        self,
        key: str,
        default: ConfigurationItem | None = None,
    ) -> ConfigurationItem | None:
        """Return a stored configuration item or a default value.

        Parameters
        ----------
        key : str
            Registry key.
        default : ConfigurationItem | None, optional
            Value returned if ``key`` does not exist.

        Returns
        -------
        ConfigurationItem | None
            Stored configuration item or ``default``.
        """

        return self._items.get(key, default)

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        """Replace an existing configuration item.

        Parameters
        ----------
        key : str
            Registry key.
        value : dict[str, Any]
            Replacement configuration data.

        Raises
        ------
        KeyError
            If ``key`` does not exist.
        TypeError
            If ``value`` is not a dictionary.
        """

        if key not in self._items:
            raise KeyError(f"No configuration stored for '{key}'.")

        if not isinstance(value, dict):
            raise TypeError("Configuration must be a dictionary.")

        self._items[key] = ConfigurationItem(
            deepcopy(value),
            validate=self._validate,
        )

    def __getattr__(self, key: str) -> ConfigurationItem:
        """Provide attribute-style access to stored items.

        Parameters
        ----------
        key : str
            Registry key.

        Returns
        -------
        ConfigurationItem
            Stored configuration item.

        Raises
        ------
        AttributeError
            If the key does not exist.
        """

        try:
            return self._items[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: Any) -> None:
        """Provide attribute-style assignment for stored items.

        Internal attributes beginning with ``_`` bypass the registry
        update machinery and are stored directly on the instance.

        Parameters
        ----------
        key : str
            Registry key or internal attribute name.
        value : Any
            Replacement value.
        """

        if key.startswith("_"):
            object.__setattr__(self, key, value)
            return

        self.__setitem__(key, value)

    def __contains__(self, key: str) -> bool:
        """Return whether a key exists in the registry."""

        return key in self._items

    def items(self) -> ItemsView[str, ConfigurationItem]:
        """Return a view of stored items."""

        return self._items.items()

    def keys(self) -> KeysView[str]:
        """Return a view of stored keys."""

        return self._items.keys()

    def values(self) -> ValuesView[ConfigurationItem]:
        """Return a view of stored configuration items."""

        return self._items.values()

    def __iter__(self) -> Iterator[str]:
        """Iterate over stored keys."""

        return iter(self._items)

    def __len__(self) -> int:
        """Return the number of stored items."""

        return len(self._items)

    def clear(self) -> None:
        """Remove all stored configuration items."""

        self._items.clear()

    def __repr__(self) -> str:
        """Return a pretty string representation of the registry."""

        if not self._items:
            return f"{self.__class__.__name__}({{}})"

        grouped: dict[str, list[str]] = defaultdict(list)

        for key, item in self._items.items():
            class_path = item.get("class_path", "unknown")
            grouped[class_path].append(key)

        lines = [f"{self.__class__.__name__}("]

        for class_path in sorted(grouped):
            lines.append(f"    {class_path}:")

            for key in sorted(grouped[class_path]):
                lines.append(f"        {key!r}")

            lines.append("")

        lines.append(")")

        return "\n".join(lines)


@dataclass(slots=True)
class ConfigurationRegistry:
    """Container grouping configuration registries by category.

    The registry separates configuration objects into logical sections
    such as controls, simulators, arrays, and devices.
    """

    data: Registry = field(default_factory=Registry)
    controls: Registry = field(default_factory=Registry)
    simulators: Registry = field(default_factory=Registry)
    arrays: Registry = field(default_factory=Registry)
    devices: Registry = field(default_factory=Registry)

    @classmethod
    def create(cls, config: dict[str, Any]) -> "ConfigurationRegistry":
        """Create a configuration registry from nested configuration data.

        Parameters
        ----------
        config : dict[str, Any]
            Top-level configuration dictionary.

        Returns
        -------
        ConfigurationRegistry
            Populated configuration registry.

        Raises
        ------
        TypeError
            If ``config`` is not a dictionary.
        """

        if not isinstance(config, dict):
            raise TypeError("Configuration must be a dictionary.")

        registry = cls()

        registry.data.add(
            "accelerator",
            {
                "class_path": "pyaml.accelerator.AcceleratorData",
                "facility": config.get("facility", ""),
                "machine": config.get("machine", ""),
                "data_folder": config.get("data_folder", ""),
                "energy": config.get("energy"),
                "alphac": config.get("alphac"),
                "harmonic_number": config.get("harmonic_number"),
            },
        )

        for item in config.get("controls", []):
            cls._add_tree(registry.controls, item)

        for item in config.get("simulators", []):
            cls._add_tree(registry.simulators, item)

        for item in config.get("arrays", []):
            cls._add_tree(registry.arrays, item)

        for item in config.get("devices", []):
            cls._add_tree(registry.devices, item)

        return registry

    @staticmethod
    def _add_tree(target: Registry, obj: Any) -> None:
        """Recursively add named configuration objects to a registry.

        Every dictionary containing a top-level ``name`` field is added
        to ``target`` under that name.

        Nested dictionaries are traversed recursively.

        Parameters
        ----------
        target : Registry
            Target registry.
        obj : Any
            Object to traverse.

        Raises
        ------
        TypeError
            If a configuration ``name`` is not a string.
        ValueError
            If nested dictionaries contain a ``name`` field.
        """

        if isinstance(obj, list):
            for item in obj:
                ConfigurationRegistry._add_tree(target, item)
            return

        if not isinstance(obj, dict):
            return

        if "name" in obj:
            name = obj["name"]
            if not isinstance(name, str):
                raise TypeError("Configuration name must be a string.")

            data = deepcopy(obj)
            data.pop("name")
            ConfigurationRegistry._check_no_nested_names(data)

            data["name"] = name
            target.add(name, data)
            logger.debug(f"Added {name} to registry {target}")

        for value in obj.values():
            ConfigurationRegistry._add_tree(target, value)

    @staticmethod
    def _check_no_nested_names(obj: Any) -> None:
        """Ensure nested dictionaries do not contain ``name`` fields.

        Parameters
        ----------
        obj : Any
            Object to validate.

        Raises
        ------
        ValueError
            If a nested dictionary contains a ``name`` field.
        """

        if isinstance(obj, list):
            for item in obj:
                ConfigurationRegistry._check_no_nested_names(item)
            return

        if not isinstance(obj, dict):
            return

        if "name" in obj:
            raise ValueError("Nested dictionaries may not contain a 'name' field.")

        for value in obj.values():
            ConfigurationRegistry._check_no_nested_names(value)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(\n"
            f"  controls={self.controls!r},\n"
            f"  simulators={self.simulators!r},\n"
            f"  arrays={self.arrays!r},\n"
            f"  devices={self.devices!r},\n"
            f")"
        )
