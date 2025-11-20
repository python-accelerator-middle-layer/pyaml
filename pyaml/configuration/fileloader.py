# PyAML config file loader
import collections.abc
import io
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Union

import yaml
from yaml import CLoader
from yaml.constructor import ConstructorError
from yaml.loader import SafeLoader

from pyaml.configuration.factory import Factory

from .. import PyAMLException

if TYPE_CHECKING:
    from pyaml.accelerator import Accelerator


logger = logging.getLogger(__name__)

accepted_suffixes = [".yaml", ".yml", ".json"]


ROOT = {"path": Path.cwd().resolve()}


def set_root_folder(path: Union[str, Path]):
    """
    Set the root path for configuration files.
    """
    ROOT["path"] = Path(path)


def get_root_folder() -> Path:
    """
    Get the root path for configuration files.
    """
    return ROOT["path"]


class PyAMLConfigCyclingException(PyAMLException):
    def __init__(self, error_filename: str, path_stack: list[Path]):
        self.error_filename = error_filename
        parent_file_stack = [parent_path.name for parent_path in path_stack]
        super().__init__(
            f"Circular file inclusion of {error_filename}. "
            f"File list before reaching it: {parent_file_stack}"
        )

    pass


def load_accelerator(filename: str, use_fast_loader: bool = False) -> "Accelerator":
    """Load an accelerator from file."""

    # Asume that all files are referenced from
    # folder where main AML file is stored
    if not os.path.exists(filename):
        raise PyAMLException(f"{filename} file not found")
    rootfolder = os.path.abspath(os.path.dirname(filename))
    set_root_folder(rootfolder)
    config_dict = load(os.path.basename(filename), None, use_fast_loader)
    aml = Factory.depth_first_build(config_dict)

    Factory.clear()
    return aml


def load(
    filename: str, paths_stack: list = None, use_fast_loader: bool = False
) -> Union[dict, list]:
    """Load recursively a configuration setup"""
    if filename.endswith(".yaml") or filename.endswith(".yml"):
        l = YAMLLoader(filename, paths_stack, use_fast_loader)
    elif filename.endswith(".json"):
        l = JSONLoader(filename, paths_stack, use_fast_loader)
    else:
        raise PyAMLException(
            f"{filename} File format not supported (only .yaml .yml or .json)"
        )
    return l.load()


# Expand condition
def hasToExpand(value):
    return isinstance(value, str) and any(
        value.endswith(suffix) for suffix in accepted_suffixes
    )


# Loader base class (nested files expansion)
class Loader:
    def __init__(self, filename: str, parent_path_stack: list[Path]):
        self.path: Path = get_root_folder() / filename
        self.files_stack: list[Path] = []
        if parent_path_stack:
            if any(
                self.path.samefile(parent_path) for parent_path in parent_path_stack
            ):
                raise PyAMLConfigCyclingException(filename, parent_path_stack)
            self.files_stack.extend(parent_path_stack)
        self.files_stack.append(self.path)

    # Recursively expand a dict
    def expand_dict(self, d: dict):
        for key, value in d.items():
            try:
                if hasToExpand(value):
                    d[key] = load(value, self.files_stack, self.use_fast_loader)
                else:
                    self.expand(value)
            except PyAMLConfigCyclingException as pyaml_ex:
                location = d.pop("__location__", None)
                field_locations = d.pop("__fieldlocations__", None)
                location_str = ""
                if location:
                    file, line, col = location
                    if field_locations and key in field_locations:
                        location = field_locations[key]
                        file, line, col = location
                    location_str = f" in {file} at line {line}, column {col}"
                raise PyAMLException(
                    "Circular file inclusion "
                    f"of {pyaml_ex.error_filename}{location_str}"
                ) from pyaml_ex

    # Recursively expand a list
    def expand_list(self, l: list):
        for idx, value in enumerate(l):
            if hasToExpand(value):
                l[idx] = load(value, self.files_stack)
            else:
                self.expand(value)

    # Recursively expand an object
    def expand(self, obj: Union[dict, list]):
        if isinstance(obj, dict):
            self.expand_dict(obj)
        elif isinstance(obj, list):
            self.expand_list(obj)
        return obj

    # Load a file
    def load(self) -> Union[dict, list]:
        raise PyAMLException(str(self.path) + ": load() method not implemented")


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
        mapping["__location__"] = (
            self.filename,
            node.start_mark.line + 1,
            node.start_mark.column + 1,
        )
        mapping["__fieldlocations__"] = field_mapping
        return mapping


# YAML loader
class YAMLLoader(Loader):
    def __init__(self, filename: str, parent_paths_stack: list, use_fast_loader: bool):
        super().__init__(filename, parent_paths_stack)
        self._loader = SafeLineLoader if not use_fast_loader else CLoader
        self.use_fast_loader = use_fast_loader

    def load(self) -> Union[dict, list]:
        logger.log(logging.DEBUG, f"Loading YAML file '{self.path}'")
        with open(self.path) as file:
            try:
                return self.expand(yaml.load(file, Loader=self._loader))
            except yaml.YAMLError as e:
                raise PyAMLException(str(self.path) + ": " + str(e)) from e


# JSON loader
class JSONLoader(Loader):
    def __init__(self, filename: str, parent_paths_stack: list, use_fast_loader: bool):
        super().__init__(filename, parent_paths_stack)
        self.use_fast_loader = False

    def load(self) -> Union[dict, list]:
        logger.log(logging.DEBUG, f"Loading JSON file '{self.path}'")
        with open(self.path) as file:
            try:
                return self.expand(json.load(file))
            except json.JSONDecodeError as e:
                raise PyAMLException(str(self.path) + ": " + str(e)) from e
