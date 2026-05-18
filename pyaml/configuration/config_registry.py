import logging
from collections.abc import ItemsView, Iterator, KeysView, ValuesView
from copy import deepcopy
from typing import Any

from .schema_registry import SchemaRegistry

logger = logging.getLogger(__name__)


class ConfigurationRegistry:
    """Singleton registry for configuration objects.

    Items are registered as name -> configuration data.
    The registry can store both validated and unvalidated data.
    """

    _instance: "ConfigurationRegistry | None" = None
    _configs: dict[str, dict[str, Any]]

    def __new__(cls) -> "ConfigurationRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._configs = {}
        return cls._instance

    def add(self, value: dict[str, Any]) -> None:
        """Add a configuration under its internal name.

        The ``name`` field is removed before storing the configuration.

        Parameters
        ----------
        value : dict[str, Any]
            Configuration data. Must contain a ``name`` field.

        Raises
        ------
        KeyError
            If ``name`` is missing.
        ValueError
            If a configuration with the same name already exists.
        TypeError
            If ``name`` is not a string.
        """
        data = dict(value)

        try:
            name = data.pop("name")
        except KeyError:
            raise KeyError("Configuration is missing a 'name' field.") from None

        if not isinstance(name, str):
            raise TypeError("Configuration name must be a string.")

        if name in self._configs:
            raise ValueError(f"Configuration '{name}' already exists.")

        self._configs[name] = data

    def _parse_path(self, path: str) -> tuple[str | int, ...]:
        """Parse a dotted/indexed update path."""
        if not path:
            raise ValueError("Path must not be empty.")

        parts: list[str | int] = []
        token: list[str] = []
        i = 0

        while i < len(path):
            char = path[i]

            if char == ".":
                if not token:
                    raise ValueError(f"Invalid path {path!r}: empty segment.")
                parts.append("".join(token))
                token.clear()
                i += 1
                continue

            if char == "[":
                if token:
                    parts.append("".join(token))
                    token.clear()

                end = path.find("]", i + 1)
                if end == -1:
                    raise ValueError(f"Invalid path {path!r}: missing ']'.")
                index_text = path[i + 1 : end]
                if not index_text.isdigit():
                    raise ValueError(f"Invalid path {path!r}: list indexes must be integers.")

                parts.append(int(index_text))
                i = end + 1
                continue

            if char == "]":
                raise ValueError(f"Invalid path {path!r}: unexpected ']'.")

            token.append(char)
            i += 1

        if token:
            parts.append("".join(token))
        elif path.endswith("."):
            raise ValueError(f"Invalid path {path!r}: trailing '.'.")

        return tuple(parts)

    def _set_in(
        self,
        data: Any,
        path: tuple[str | int, ...],
        value: Any,
    ) -> Any:
        """Return a copy of data with one nested value replaced."""
        if not path:
            return deepcopy(value)

        head, *tail = path

        if isinstance(data, dict):
            if not isinstance(head, str):
                raise TypeError("Dictionary path segments must be strings.")
            if head not in data:
                raise KeyError(f"Key '{head}' does not exist.")

            updated = dict(data)
            updated[head] = self._set_in(updated[head], tuple(tail), value)
            return updated

        if isinstance(data, list):
            if not isinstance(head, int):
                raise TypeError("List path segments must be integers.")
            if head < 0 or head >= len(data):
                raise IndexError(f"List index {head} out of range.")

            updated = list(data)
            updated[head] = self._set_in(updated[head], tuple(tail), value)
            return updated

        raise TypeError(f"Cannot descend into object of type {type(data).__name__}.")

    def update(
        self,
        name: str,
        path: str | None,
        value: Any,
        *,
        validate: bool = True,
    ) -> None:
        """Update a stored configuration.

        Parameters
        ----------
        name : str
            Registry name.
        path : str | None, optional
            Dotted/indexed path to the nested value to update. If
            ``None``, replace the entire configuration.
        value : Any
            Replacement value.
        validate : bool, optional
            If ``True``, validate the updated configuration with
            :class:`SchemaRegistry` before storing it.
        """
        current = deepcopy(self._configs[name])

        if path is None:
            if not isinstance(value, dict):
                raise TypeError("Replacing a configuration requires a dictionary.")
            updated = dict(value)
        else:
            parsed_path = self._parse_path(path)
            updated = self._set_in(current, parsed_path, value)

        if not isinstance(updated, dict):
            raise TypeError("Top-level configuration must remain a dictionary.")

        if validate:
            candidate = dict(updated)
            candidate["name"] = name
            validated = SchemaRegistry().validate(candidate)
            self._configs[name] = validated.model_dump(exclude={"name"})
        else:
            self._configs[name] = updated

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename a stored configuration."""
        if old_name not in self._configs:
            raise KeyError(f"No configuration stored for '{old_name}'.")

        if new_name in self._configs:
            raise ValueError(f"Configuration '{new_name}' already exists.")

        self._configs[new_name] = self._configs.pop(old_name)

    def __getitem__(self, name: str) -> dict[str, Any]:
        """Return the stored configuration for a name."""
        return self._configs[name]

    def get(self, name: str, default: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Return the stored configuration for a name."""
        return self._configs.get(name, default)

    def __contains__(self, name: str) -> bool:
        return name in self._configs

    def items(self) -> ItemsView[str, dict[str, Any]]:
        return self._configs.items()

    def keys(self) -> KeysView[str]:
        return self._configs.keys()

    def values(self) -> ValuesView[dict[str, Any]]:
        return self._configs.values()

    def __iter__(self) -> Iterator[str]:
        return iter(self._configs)

    def __len__(self) -> int:
        return len(self._configs)

    def clear(self) -> None:
        """Remove all stored configurations."""
        self._configs.clear()

    def __repr__(self) -> str:
        """Return a pretty representation of the registry."""
        if not self._configs:
            return f"{self.__class__.__name__}({{}})"

        lines = [f"{self.__class__.__name__}("]

        for name in sorted(self._configs):
            lines.append(f"    {name!r}: dict,")

        lines.append(")")

        return "\n".join(lines)
