"""PyAML configuration file loader."""

import collections.abc
import io
import json
import logging
from abc import ABC, abstractmethod
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

ACCEPTED_SUFFIXES = (".yaml", ".yml", ".json")
FILE_PREFIX = "file:"

LOCATION_KEY = "__location__"
FIELD_LOCATIONS_KEY = "__fieldlocations__"


class RootFolder:
    """
    Manage the root directory used to resolve relative configuration paths.
    """

    def __init__(self, path: str | Path | None = None):
        # Resolve the path is given otherwise set to the current working directory
        if path is None:
            self._path = Path.cwd().resolve()
        else:
            self._path = Path(path).resolve()

    def set(self, path: str | Path) -> None:
        """
        Set the root path for configuration files.
        """
        self._path = Path(path).resolve()

    def get(self) -> Path:
        """
        Get the root path for configuration files.
        """
        return self._path

    def expand_path(self, path: str | Path) -> Path:
        """
        Return an absolute configuration path.

        Relative paths are interpreted relative to the configured root
        folder. Absolute paths are returned unchanged.
        """

        path = Path(path)
        if not path.is_absolute():
            path = self._path / path
        return path.resolve()


ROOT = RootFolder()


class PyAMLConfigCyclingException(PyAMLException):
    def __init__(self, error_filename: str, path_stack: list[Path]):
        self.error_filename = error_filename

        parent_file_stack = [parent_path.name for parent_path in path_stack]
        super().__init__(f"Circular file inclusion of {error_filename}. File list before reaching it: {parent_file_stack}")


@dataclass
class LoadContext:
    use_fast_loader: bool = False
    include_stack: list[Path] = field(default_factory=list)

    @contextmanager
    def loading(self, path: Path):
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


def load(filename: str, use_fast_loader: bool = False) -> Union[dict, list]:
    """Load recursively a configuration setup."""

    # Create a new context
    context = LoadContext(use_fast_loader=use_fast_loader)

    return _load(filename, context)


def _load(filename: str, context: LoadContext) -> Union[dict, list]:
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
    """Return True if the value is a supported configuration file."""
    return isinstance(value, str) and value.endswith(ACCEPTED_SUFFIXES)


class ConfigLoader(ABC):
    def __init__(self, path: Path, context: LoadContext):
        self.path = path
        self.context = context

    def expand(self, obj: Union[dict, list, Any]) -> Union[dict, list, Any]:
        if isinstance(obj, dict):
            return self._expand_dict(obj)
        if isinstance(obj, list):
            return self._expand_list(obj)
        return obj

    def _expand_dict(self, d: dict) -> dict:
        for key, value in list(d.items()):
            try:
                if _is_supported_file(value):
                    # If it is a reference to another file
                    resolved = self._resolve_file_reference(value)
                    if resolved is not None:
                        d[key] = resolved
                    else:
                        d[key] = _load(value, self.context)
                else:
                    d[key] = self.expand(value)
            except PyAMLConfigCyclingException as exc:
                self._raise_cycle_error(exc, d, key)

        return d

    def _resolve_file_reference(self, value: str) -> str | None:
        """Return an absolute path for FILE_PREFIX references, otherwise None."""

        if value.startswith(FILE_PREFIX):
            stripped_value = value[len(FILE_PREFIX) :]
            return str(ROOT.get() / Path(stripped_value))
        return None

    def _raise_cycle_error(self, exc: PyAMLConfigCyclingException, obj: dict, key: Any) -> None:
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
        expanded = []
        for value in items:
            if _is_supported_file(value):
                loaded = _load(value, self.context)
                if isinstance(loaded, list):
                    expanded.extend(loaded)
                else:
                    expanded.append(loaded)
            else:
                expanded.append(self.expand(value))
        return expanded

    @abstractmethod
    def load(self) -> Union[dict, list]: ...


class YAMLLoader(ConfigLoader):
    def __init__(self, path: Path, context: LoadContext):
        super().__init__(path, context)
        self._loader = CLoader if context.use_fast_loader else SafeLineLoader

    def load(self) -> Union[dict, list]:
        logger.log(logging.DEBUG, f"Loading YAML file '{self.path}'")
        with open(self.path) as file:
            try:
                return self.expand(yaml.load(file, Loader=self._loader))
            except yaml.YAMLError as exc:
                raise PyAMLException(f"{self.path}: {exc}") from exc


class JSONLoader(ConfigLoader):
    def __init__(self, path: Path, context: LoadContext):
        super().__init__(path, context)

    def load(self) -> Union[dict, list]:
        logger.log(logging.DEBUG, f"Loading JSON file '{self.path}'")
        with open(self.path) as file:
            try:
                return self.expand(json.load(file))
            except json.JSONDecodeError as exc:
                raise PyAMLException(f"{self.path}: {exc}") from exc


class SafeLineLoader(SafeLoader):
    def __init__(self, stream):
        super().__init__(stream)
        self.filename = stream.name if isinstance(stream, io.TextIOWrapper) else ""

    def construct_mapping(self, node, deep=False):
        mapping = {}
        field_mapping = {}

        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, collections.abc.Hashable):
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
