"""PyAML configuration file loader."""

import io
import json
import logging
import os
import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Hashable
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

import yaml
from yaml import CLoader
from yaml.constructor import ConstructorError
from yaml.loader import SafeLoader

from .. import PyAMLException

logger = logging.getLogger(__name__)


LOCATION_KEY = "__location__"
FIELD_LOCATIONS_KEY = "__fieldlocations__"
ACCEPTED_SUFFIXES = (".yaml", ".yml", ".json")
RESOLVER_PATTERN = re.compile(r"\$\{([^{}]+)\}")

FILE_PREFIX = "file:"  # Kept for compatibility reasons with other modules


class RootFolder:
    """Manage the root directory used to resolve configuration paths."""

    def __init__(self, path: str | Path | None = None):
        """Create a root folder.

        If no path is provided, the current working directory is used.
        """
        if path is None:
            self._path = Path.cwd().resolve()
        else:
            self._path = Path(path).resolve()

    def set(self, path: str | Path) -> None:
        """Set the root path used for resolving relative configuration files."""
        self._path = Path(path).resolve()

    def get(self) -> Path:
        """Return the current root path."""
        return self._path

    def expand_path(self, path: str | Path) -> Path:
        """Return an absolute, normalized configuration path.

        Relative paths are interpreted relative to the configured root folder.
        """

        path = Path(path)
        if not path.is_absolute():
            path = self._path / path
        return path.resolve()


ROOT = RootFolder()


class PyAMLConfigCyclingException(PyAMLException):
    """Raised when a configuration file includes itself through a cycle."""

    def __init__(self, error_filename: str, path_stack: list[Path]):
        """Create a circular-include error.

        Args:
            error_filename: The file that triggered the cycle.
            path_stack: The include chain leading to the cycle.
        """

        self.error_filename = error_filename

        parent_file_stack = [parent_path.name for parent_path in path_stack]
        super().__init__(f"Circular file inclusion of {error_filename}. File list before reaching it: {parent_file_stack}")


@dataclass
class LoadContext:
    """Track state for one recursive configuration-loading session."""

    include_locations: bool = False
    include_stack: list[Path] = field(default_factory=list)

    @contextmanager
    def loading(self, path: Path):
        """Register a file as currently being loaded and remove it afterward.

        Raises:
            PyAMLConfigCyclingException: If the file is already on the active
                include stack.
        """

        # Check if the file is currently in the chain
        # Raise a cycling error if that is the case
        if path in self.include_stack:
            raise PyAMLConfigCyclingException(path.name, self.include_stack)

        # Add the file to the stack to record that it is now being loaded
        self.include_stack.append(path)
        try:
            # Run the code in the with block
            yield
        finally:
            # Remove the file to stack to record that it has finished loading
            self.include_stack.pop()


Resolver = Callable[[str, LoadContext | None], Any]
RESOLVERS: dict[str, Resolver] = {}


def resolver(name: str):
    """Register a function as a configuration value resolver.

    Args:
        name: Prefix used to invoke the resolver (for example ``"env"``
            or ``"file"``).

    Returns:
        A decorator that registers the decorated function in the global
        resolver registry.
    """

    def decorate(func: Resolver) -> Resolver:
        RESOLVERS[name] = func
        return func

    return decorate


@resolver("env")
def resolve_env(value: str, _context: LoadContext | None = None) -> str:
    """Resolve an environment variable.

    Args:
        value: Name of the environment variable.
        context: Unused loading context. Present to match the resolver
            interface.

    Raises:
        PyAMLException: If the environment variable is not set.
    """
    try:
        return os.environ[value]
    except KeyError as exc:
        raise PyAMLException(f"Environment variable '{value}' is not set") from exc


@resolver("file")
def resolve_file(value: str, context: LoadContext) -> Any:
    """Load and return the contents of a configuration file.

    Args:
        value: Path to the configuration file.
        context: Shared loading context used to track recursive includes
            and detect inclusion cycles.

    Raises:
        RuntimeError: If no loading context is provided.
    """
    if context is None:
        raise RuntimeError("File resolver requires LoadContext")
    return _load(value, context)


def load(filename: str, include_locations: bool = False) -> Union[dict, list]:
    """Load a configuration file.

    When include_locations is False, uses the faster C-based YAML loader
    and skips including source location metadata.
    """

    # Create a new context
    context = LoadContext(include_locations=include_locations)

    return _load(filename, context)


def _load(filename: str, context: LoadContext) -> Union[dict, list]:
    """Load a single configuration file using the appropriate parser."""

    path = ROOT.expand_path(filename)

    with context.loading(path):
        if filename.endswith((".yaml", ".yml")):
            loader = YAMLLoader(path, context)
        elif filename.endswith(".json"):
            loader = JSONLoader(path, context)
        else:
            raise PyAMLException(f"{filename} File format not supported (only .yaml .yml or .json)")

        return loader.load()


def _is_supported_file(value: Any) -> bool:
    """Return True if the value looks like a supported configuration file name."""
    return isinstance(value, str) and value.endswith(ACCEPTED_SUFFIXES)


class ConfigLoader(ABC):
    """Base class for loaders that expand nested configuration references."""

    def __init__(self, path: Path, context: LoadContext):
        """Store the file path and shared loading context."""

        self.path = path
        self.context = context

    def expand(self, obj: Union[dict, list, Any]) -> Union[dict, list, Any]:
        """Recursively expand configuration values.

        Dictionaries and lists are traversed recursively, while string values
        are resolved using the registered resolvers. All other values are
        returned unchanged.
        """

        if isinstance(obj, dict):
            return self._expand_dict(obj)
        if isinstance(obj, list):
            return self._expand_list(obj)
        if isinstance(obj, str):
            return self._expand_string(obj)
        return obj

    def _expand_string(self, value: str) -> Any:
        """Expand resolver expressions and file references in a string.

        If the entire string is a resolver expression (for example
        ``"${env:HOME}"`` or ``"${file:config.yaml}"``), the resolved value is
        returned directly and may be of any type.

        Resolver expressions embedded inside a larger string are interpolated
        into the surrounding text. Only scalar values may be interpolated;
        attempting to embed a dictionary or list raises a ``PyAMLException``.

        After resolver expansion, plain strings that refer to supported
        configuration files are loaded automatically.

        Args:
            value: The string value to expand.

        Returns:
            The expanded value, which may be a string or another object if the
            input consists solely of a resolver expression.
        """

        full_match = RESOLVER_PATTERN.fullmatch(value)
        if full_match:
            return self._resolve_resolver_expression(full_match.group(1).strip())

        # Handle embedded case
        def replace(match: re.Match[str]) -> str:
            resolved = self._resolve_resolver_expression(match.group(1).strip())

            if isinstance(resolved, (dict, list)):
                raise PyAMLException(
                    f"Resolver '{match.group(1)}' returned a {type(resolved).__name__}, "
                    "which cannot be interpolated into a string."
                )

            return str(resolved)

        value = RESOLVER_PATTERN.sub(replace, value)

        if _is_supported_file(value):
            return RESOLVERS["file"](value, self.context)

        return value

    def _resolve_resolver_expression(self, expr: str) -> Any:
        """Resolve a single resolver expression.

        The expression must have the form ``"<resolver>:<payload>"``, for
        example ``"env:HOME"`` or ``"file:config.yaml"``. The resolver is
        looked up in the global resolver registry and invoked with the
        supplied payload.

        Args:
            expr: Resolver expression without the surrounding ``"${...}"``.

        Returns:
            The value returned by the matching resolver.

        Raises:
            PyAMLException: If the expression is malformed or references an
                unknown resolver.
        """
        if ":" not in expr:
            raise PyAMLException(f"Invalid resolver expression '{expr}'")

        prefix, payload = expr.split(":", 1)
        resolver = RESOLVERS.get(prefix.strip())
        if resolver is None:
            raise PyAMLException(f"Unknown resolver '{prefix.strip()}'")

        return resolver(payload.strip(), self.context)

    def _expand_dict(self, data: dict) -> dict:
        """Recursively expand dictionary values and enrich cycle errors with location information."""

        for key, value in list(data.items()):
            try:
                data[key] = self.expand(value)
            except PyAMLConfigCyclingException as exc:
                self._raise_cycle_error(exc, data, key)
        return data

    def _raise_cycle_error(self, exc: PyAMLConfigCyclingException, obj: dict, key: Any) -> None:
        """Re-raise a cycle error with file location information, if available."""

        location = obj.get(LOCATION_KEY)
        field_locations = obj.get(FIELD_LOCATIONS_KEY)

        location_str = ""
        if location:
            file, line, col = location
            if field_locations and key in field_locations:
                file, line, col = field_locations[key]
            location_str = f" in {file} at line {line}, column {col}"

        raise PyAMLException(f"Circular file inclusion of {exc.error_filename}{location_str}") from exc

    def _expand_list(self, items: list) -> list:
        """Recursively expand the elements of a list.

        Plain string values that refer to supported configuration files are
        treated as list includes. If the referenced file loads to a list, its
        elements are spliced into the current list. Otherwise, the loaded
        object is appended as a single element.

        All other items are expanded recursively using :meth:`expand`.

        Args:
            items: The list to expand.

        Returns:
            The expanded list.
        """
        expanded: list[Any] = []

        for item in items:
            if isinstance(item, str) and _is_supported_file(item):
                loaded = RESOLVERS["file"](item, self.context)
                if isinstance(loaded, list):
                    expanded.extend(loaded)
                else:
                    expanded.append(loaded)
                continue

            expanded.append(self.expand(item))

        return expanded

    @abstractmethod
    def load(self) -> Union[dict, list]:
        """Load and parse the current configuration file."""
        ...


class YAMLLoader(ConfigLoader):
    """Load and expand YAML configuration files."""

    def __init__(self, path: Path, context: LoadContext):
        """Create a YAML loader for the given file."""

        super().__init__(path, context)
        self._loader = SafeLineLoader if context.include_locations else CLoader

    def load(self) -> Union[dict, list]:
        """Parse the YAML file and expand nested configuration references."""

        logger.log(logging.DEBUG, f"Loading YAML file '{self.path}'")
        with open(self.path) as file:
            try:
                return self.expand(yaml.load(file, Loader=self._loader))
            except yaml.YAMLError as exc:
                raise PyAMLException(f"{self.path}: {exc}") from exc


class JSONLoader(ConfigLoader):
    """Load and expand JSON configuration files."""

    def __init__(self, path: Path, context: LoadContext):
        """Create a JSON loader for the given file."""

        super().__init__(path, context)

    def load(self) -> Union[dict, list]:
        """Parse the JSON file and expand nested configuration references."""

        logger.log(logging.DEBUG, f"Loading JSON file '{self.path}'")
        with open(self.path) as file:
            try:
                return self.expand(json.load(file))
            except json.JSONDecodeError as exc:
                raise PyAMLException(f"{self.path}: {exc}") from exc


class SafeLineLoader(SafeLoader):
    """YAML loader that preserves line and column information for mappings."""

    def __init__(self, stream):
        """Create the YAML loader and record the source filename."""

        super().__init__(stream)
        self.filename = stream.name if isinstance(stream, io.TextIOWrapper) else ""

    def construct_mapping(self, node, deep=False):
        """Build a mapping and attach location metadata to it."""

        mapping = {}
        field_mapping = {}

        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, Hashable):
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found unhashable key",
                    key_node.start_mark,
                )

            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
            field_mapping[key] = (
                self.filename,
                value_node.start_mark.line + 1,
                value_node.start_mark.column + 1,
            )

        # Add location information inside the dict
        mapping[LOCATION_KEY] = (
            self.filename,
            node.start_mark.line + 1,
            node.start_mark.column + 1,
        )
        mapping[FIELD_LOCATIONS_KEY] = field_mapping
        return mapping
