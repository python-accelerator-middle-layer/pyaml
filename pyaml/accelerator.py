"""
Accelerator class
"""

import json
import os
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import ProxyHandler, build_opener

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .arrays.array import ArrayConfig
from .common.element import Element
from .common.element_holder import ElementHolder
from .common.exception import PyAMLConfigException
from .configuration.factory import Factory
from .configuration.fileloader import get_root_folder, load, set_root_folder
from .control.controlsystem import ControlSystem
from .lattice.simulator import Simulator
from .yellow_pages import YellowPages

# Define the main class name for this module
PYAMLCLASS = "Accelerator"


class ConfigModel(BaseModel):
    """
    Configuration model for Accelerator

    Parameters
    ----------
    facility : str
        Facility name
    machine : str
        Accelerator name
    energy : float
        Accelerator nominal energy. For ramped machine,
        this value can be dynamically set
    alphac : float, optional
        Moment compaction factor.
    controls : list[ControlSystem], optional
        List of control system used. An accelerator
        can access several control systems
    simulators : list[Simulator], optional
        Simulator list
    data_folder : str
        Data folder
    arrays : list[ArrayConfig], optional
        Element family
    description : str , optional
        Acceleration description
    devices : list[.common.element.Element]
        Element list
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    facility: str | None = None
    machine: str | None = None
    energy: float | None = None
    alphac: float | None = None
    controls: list[ControlSystem] | None = None
    simulators: list[Simulator] | None = None
    data_folder: str | None = None
    description: str | None = None
    arrays: list[ArrayConfig] | None = Field(default=None, repr=False)
    devices: list[Element] | None = Field(default=None, repr=False)


def _is_url(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https"}


def _get_source_root_folder(source) -> Path | None:
    if isinstance(source, os.PathLike):
        source = os.fspath(source)

    if isinstance(source, str) and not _is_url(source):
        return Path(source).resolve().parent

    return None


def _sanitize_config(value):
    if isinstance(value, dict):
        return {
            key: _sanitize_config(val)
            for key, val in value.items()
            if key not in {"__location__", "__fieldlocations__"}
        }
    if isinstance(value, list):
        return [_sanitize_config(item) for item in value]
    return value


def _extract_key_path(payload, key: str):
    current = payload
    for part in key.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise PyAMLConfigException(f"Config key '{key}' not found")
            current = current[part]
            continue

        if isinstance(current, list):
            if part.isdigit():
                index = int(part)
                if index >= len(current):
                    raise PyAMLConfigException(f"Config key '{key}' not found")
                current = current[index]
                continue

            matches = [item for item in current if isinstance(item, dict) and item.get("name") == part]
            if len(matches) == 1:
                current = matches[0]
                continue
            if len(matches) > 1:
                raise PyAMLConfigException(f"Config key '{key}' is ambiguous")
            raise PyAMLConfigException(f"Config key '{key}' not found")

        raise PyAMLConfigException(f"Config key '{key}' cannot be resolved")

    return _sanitize_config(deepcopy(current))


def _wrap_key_fragment(payload, key: str):
    if "." not in key:
        return {key: _extract_key_path(payload, key)}

    top_key = key.split(".", 1)[0]
    top_value = payload.get(top_key) if isinstance(payload, dict) else None
    extracted = _extract_key_path(payload, key)

    if isinstance(top_value, list):
        return {top_key: [extracted]}

    return {top_key: extracted}


def _merge_list(target: list, incoming: list) -> list:
    merged = deepcopy(target)

    for item in incoming:
        if not isinstance(item, dict):
            if item not in merged:
                merged.append(deepcopy(item))
            continue

        name = item.get("name")
        if name is None:
            merged.append(deepcopy(item))
            continue

        replaced = False
        for index, current in enumerate(merged):
            if isinstance(current, dict) and current.get("name") == name:
                merged[index] = deepcopy(item)
                replaced = True
                break
        if not replaced:
            merged.append(deepcopy(item))

    return merged


def _merge_config(target: dict, fragment: dict) -> dict:
    merged = deepcopy(target)

    for key, value in fragment.items():
        if key not in merged:
            merged[key] = deepcopy(value)
        elif isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_config(merged[key], value)
        elif isinstance(merged[key], list) and isinstance(value, list):
            merged[key] = _merge_list(merged[key], value)
        else:
            merged[key] = deepcopy(value)

    return merged


def _remove_from_list(target: list, fragment: list, section: str) -> list:
    updated = deepcopy(target)

    for item in fragment:
        if not isinstance(item, dict):
            if item not in updated:
                raise PyAMLConfigException(f"Cannot remove unknown entry from '{section}'")
            updated.remove(item)
            continue

        name = item.get("name")
        if name is None:
            raise PyAMLConfigException(f"Removal from '{section}' requires named entries or exact scalar values")

        index = next(
            (idx for idx, current in enumerate(updated) if isinstance(current, dict) and current.get("name") == name),
            None,
        )
        if index is None:
            raise PyAMLConfigException(f"Cannot remove unknown entry '{name}' from '{section}'")
        updated.pop(index)

    return updated


def _remove_config(target: dict, fragment: dict) -> dict:
    updated = deepcopy(target)

    for key, value in fragment.items():
        if key not in updated:
            raise PyAMLConfigException(f"Cannot remove unknown config section '{key}'")

        current = updated[key]
        if isinstance(current, list) and isinstance(value, list):
            updated[key] = _remove_from_list(current, value, key)
            continue

        if isinstance(current, dict) and isinstance(value, dict):
            updated[key] = _remove_config(current, value)
            if updated[key] == {}:
                del updated[key]
            continue

        if value is not None and current != value:
            raise PyAMLConfigException(f"Cannot remove '{key}': current value does not match")
        del updated[key]

    return updated


def _read_remote_payload(source: str):
    opener = build_opener(ProxyHandler({}))
    with opener.open(source) as response:
        payload = response.read().decode(response.headers.get_content_charset() or "utf-8")
        content_type = response.headers.get_content_type()

    if content_type == "application/json" or source.endswith(".json"):
        return json.loads(payload)

    try:
        return yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        raise PyAMLConfigException(f"Unable to parse remote config from {source}") from exc


class Accelerator(object):
    """PyAML top level class"""

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self._config_dict: dict = {"type": "pyaml.accelerator"}
        self._ignore_external = False
        self._root_folder = get_root_folder()
        self.__design = None
        self.__live = None
        self._controls: dict[str, ElementHolder] = {}
        self._simulators: dict[str, ElementHolder] = {}
        devices = cfg.devices or []

        if cfg.controls is not None:
            for c in cfg.controls:
                if c.name() == "live":
                    self.__live = c
                else:
                    # Add as dynamic attribute
                    setattr(self, c.name(), c)
                c.fill_device(devices)
                self._controls[c.name()] = c

        if cfg.simulators is not None:
            for s in cfg.simulators:
                if s.name() == "design":
                    self.__design = s
                else:
                    # Add as dynamic attribute
                    setattr(self, s.name(), s)
                s.fill_device(devices)
                self._simulators[s.name()] = s

        if cfg.arrays is not None:
            for a in cfg.arrays:
                if cfg.simulators is not None:
                    for s in cfg.simulators:
                        a.fill_array(s)
                if cfg.controls is not None:
                    for c in cfg.controls:
                        a.fill_array(c)

        if cfg.energy is not None:
            self.set_energy(cfg.energy)

        if cfg.alphac is not None:
            self.set_mcf(cfg.alphac)

        self._yellow_pages = YellowPages(self)

        self.post_init()

    def set_energy(self, E: float):
        """
        Set the energy for all simulators and control systems.

        Parameters
        ----------
        E : float
            Energy value to set in eV
        """
        if self._cfg.simulators is not None:
            for s in self._cfg.simulators:
                s._set_energy(E)
        if self._cfg.controls is not None:
            for c in self._cfg.controls:
                c._set_energy(E)

    def set_mcf(self, alphac: float):
        """
        Set the moment compaction factor for all simulators and control systems.

        Parameters
        ----------
        alphac : float
            Moment compaction factor
        """
        if self._cfg.simulators is not None:
            for s in self._cfg.simulators:
                s._set_mcf(alphac)
        if self._cfg.controls is not None:
            for c in self._cfg.controls:
                c._set_mcf(alphac)

    def post_init(self):
        """
        Method triggered after all initialisations are done
        """
        if self._cfg.simulators is not None:
            for s in self._cfg.simulators:
                s.post_init()
        if self._cfg.controls is not None:
            for c in self._cfg.controls:
                c.post_init()

    def get_description(self) -> str:
        """
        Returns the description of the accelerator
        """
        return self._cfg.description

    @property
    def live(self) -> ControlSystem:
        """
        Get the live control system.

        Returns
        -------
        ControlSystem
            The live control system instance
        """
        return self.__live

    @property
    def design(self) -> Simulator:
        """
        Get the design simulator.

        Returns
        -------
        Simulator
            The design simulator instance
        """
        return self.__design

    @property
    def yellow_pages(self) -> YellowPages:
        return self._yellow_pages

    def simulators(self) -> dict[str, "ElementHolder"]:
        """Return all registered simulator modes."""
        return self._simulators

    def controls(self) -> dict[str, "ElementHolder"]:
        """Return all registered control modes."""
        return self._controls

    def modes(self) -> dict[str, "ElementHolder"]:
        """Return all registered control and simulator modes."""
        modes: dict[str, "ElementHolder"] = {}
        modes.update(self._simulators)
        modes.update(self._controls)
        return modes

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)

    def to_dict(self) -> dict:
        """
        Return a deep copy of the current raw accelerator configuration.
        """
        return deepcopy(self._config_dict)

    @staticmethod
    def empty(ignore_external=False) -> "Accelerator":
        """
        Create an empty accelerator that can be enriched incrementally.
        """
        return Accelerator.from_dict({"type": "pyaml.accelerator"}, ignore_external=ignore_external)

    @staticmethod
    def fetch_config(source, key: str | None = None):
        """
        Fetch raw configuration from a local YAML/JSON file or a remote URL.
        """
        if isinstance(source, os.PathLike):
            source = os.fspath(source)

        if isinstance(source, dict):
            payload = _sanitize_config(deepcopy(source))
        elif isinstance(source, str):
            if _is_url(source):
                payload = _sanitize_config(_read_remote_payload(source))
            else:
                source_path = Path(source)
                if not source_path.exists():
                    raise PyAMLConfigException(f"{source} file not found")

                previous_root = get_root_folder()
                rootfolder = os.path.abspath(os.path.dirname(source))
                set_root_folder(rootfolder)
                try:
                    payload = _sanitize_config(load(os.path.basename(source), None, False))
                finally:
                    set_root_folder(previous_root)
        else:
            raise PyAMLConfigException("Config source must be a dict, local path, or URL")

        if key is None:
            return deepcopy(payload)

        return _extract_key_path(payload, key)

    def add_config(self, source, key: str | None = None) -> "Accelerator":
        """
        Merge configuration into the current accelerator and update it atomically.
        """
        source_root = _get_source_root_folder(source)
        fragment = self._resolve_config_source(source, key)
        candidate_config = _merge_config(self.to_dict(), fragment)
        candidate = self._rebuild_from_config(candidate_config, source_root=source_root)
        self._replace_state(candidate)
        return self

    def remove_config(self, source, key: str | None = None) -> "Accelerator":
        """
        Remove configuration from the current accelerator and update it atomically.
        """
        source_root = _get_source_root_folder(source)
        fragment = self._resolve_config_source(source, key)
        candidate_config = _remove_config(self.to_dict(), fragment)
        candidate = self._rebuild_from_config(candidate_config, source_root=source_root)
        self._replace_state(candidate)
        return self

    def _resolve_config_source(self, source, key: str | None) -> dict:
        if isinstance(source, dict):
            payload = _sanitize_config(deepcopy(source))
        else:
            payload = Accelerator.fetch_config(source)

        if key is None:
            if not isinstance(payload, dict):
                raise PyAMLConfigException("Config fragments must resolve to dictionaries")
            return payload

        wrapped = _wrap_key_fragment(payload, key)
        if not isinstance(wrapped, dict):
            raise PyAMLConfigException("Config fragments must resolve to dictionaries")
        return wrapped

    def _rebuild_from_config(self, config_dict: dict, source_root: Path | None = None) -> "Accelerator":
        previous_root = get_root_folder()
        rebuild_root = self._root_folder
        if source_root is not None and self.to_dict() == {"type": "pyaml.accelerator"}:
            rebuild_root = source_root
        set_root_folder(rebuild_root)
        try:
            return Accelerator.from_dict(config_dict, ignore_external=self._ignore_external)
        finally:
            set_root_folder(previous_root)

    def _replace_state(self, other: "Accelerator") -> None:
        previous_dynamic_attrs = set(self._controls.keys()) | set(self._simulators.keys())
        for name in previous_dynamic_attrs:
            if name not in {"live", "design"} and hasattr(self, name):
                delattr(self, name)

        self._cfg = other._cfg
        self._controls = other._controls
        self._simulators = other._simulators
        self._config_dict = other.to_dict()
        self._ignore_external = other._ignore_external
        self._root_folder = other._root_folder
        self.__live = other.__live
        self.__design = other.__design
        self._yellow_pages = YellowPages(self)

        for name, holder in self.modes().items():
            if name not in {"live", "design"}:
                setattr(self, name, holder)

    @staticmethod
    def from_dict(config_dict: dict, ignore_external=False) -> "Accelerator":
        """
        Construct an accelerator from a dictionary.

        Parameters
        ----------
        config_dict : str
            Dictionary containing accelerator config
        ignore_external: bool
            Ignore external modules and return None for object that
            cannot be created. pydantic schema that support that an
            object is not created should handle None fields.
        """
        raw_config = _sanitize_config(deepcopy(config_dict))
        effective_config = deepcopy(config_dict)
        if ignore_external:
            # control systems are external, so remove controls field
            effective_config.pop("controls", None)
            raw_config.pop("controls", None)
        # Ensure factory is clean before building a new accelerator
        Factory.clear()
        accelerator = Factory.depth_first_build(effective_config, ignore_external)
        if isinstance(accelerator, Accelerator):
            accelerator._config_dict = raw_config
            accelerator._ignore_external = ignore_external
            accelerator._root_folder = get_root_folder()
        return accelerator

    @staticmethod
    def load(filename: str, use_fast_loader: bool = False, ignore_external=False) -> "Accelerator":
        """
        Load an accelerator from a config file.

        Parameters
        ----------
        filename : str
            Configuration file name, yaml or json.
        use_fast_loader : bool
            Use fast yaml loader. When specified,
            no line number are reported in case of error,
            only the element name that triggered the error
            will be reported in the exception)
        ignore_external : bool
            Ignore external modules and return None for object that
            cannot be created. pydantic schema that support that an
            object is not created should handle None fields.
        """
        # Asume that all files are referenced from
        # folder where main AML file is stored
        if not os.path.exists(filename):
            raise PyAMLConfigException(f"{filename} file not found")
        rootfolder = os.path.abspath(os.path.dirname(filename))
        set_root_folder(rootfolder)
        config_dict = load(os.path.basename(filename), None, use_fast_loader)
        return Accelerator.from_dict(config_dict, ignore_external=ignore_external)
