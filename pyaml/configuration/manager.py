"""
manager.py

Configuration aggregation helpers for :class:`~pyaml.accelerator.Accelerator`.

This module provides :class:`ConfigurationManager`, a lightweight service used
to collect configuration fragments before runtime objects are built.

Typical usage is:

- load one or more accelerator configuration fragments
- inspect or query the aggregated state
- build the final :class:`~pyaml.accelerator.Accelerator`
"""

import copy
import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from ..common.exception import PyAMLConfigException
from .fileloader import get_root_folder, load, set_root_folder
from .restfetcher import REMOTE_BASE_URL_KEY, SourceRoot, fetch_remote_config, is_remote_url, resolve_reference

_INTERNAL_METADATA_KEYS = {"__location__", "__fieldlocations__", REMOTE_BASE_URL_KEY}
_VALID_QUERY_KEY_RE = re.compile(r"^[A-Z0-9_]+$")
_CATEGORY_TITLES = {
    "controls": "Controls",
    "catalogs": "Catalogs",
    "simulators": "Simulators",
    "arrays": "Arrays",
    "devices": "Devices",
}


class UnsupportedConfigurationRootError(PyAMLConfigException):
    """Raised when a fragment root is outside ConfigurationManager scope."""


class ConfigurationManager:
    r"""
    Aggregate accelerator configuration fragments before runtime build.

    :class:`ConfigurationManager` stores configuration fragments as plain
    dictionaries and exposes convenience helpers to inspect, query and update
    them before constructing the final runtime object graph.

    Notes
    -----
    The manager only accepts accelerator-root fragments and merges named
    categories such as ``controls``, ``catalogs``, ``simulators``,
    ``arrays`` and ``devices``.

    Examples
    --------

    Load a base configuration and inspect it:

    .. code-block:: python

        >>> from pyaml.configuration import ConfigurationManager
        >>> manager = ConfigurationManager()
        >>> manager.add("tests/config/config_manager_base.yaml")
        >>> manager.categories()
        ['simulators']

    Build the final accelerator:

    .. code-block:: python

        >>> sr = manager.build()
        >>> sr.design.name()
        'design'
    """

    DEFAULT_TYPE = "pyaml.accelerator"
    NAMED_CATEGORIES = ("controls", "catalogs", "simulators", "arrays", "devices")
    _SUPPORTED_FILE_SUFFIXES = {".yaml", ".yml", ".json"}

    @classmethod
    def root_fields(cls) -> tuple[str, ...]:
        r"""
        Return the ordered root fields supported by the accelerator model.

        The field order is derived from
        :class:`~pyaml.accelerator.ConfigModel`.

        Returns
        -------
        tuple[str, ...]

        Examples
        --------

        .. code-block:: python

            >>> ConfigurationManager.root_fields()
        """
        from ..accelerator import ConfigModel as AcceleratorConfigModel

        config_fields = tuple(
            field_name for field_name in AcceleratorConfigModel.model_fields if field_name not in cls.NAMED_CATEGORIES
        )
        return ("type", *config_fields)

    def __init__(self):
        self._state: dict[str, Any] = {"type": self.DEFAULT_TYPE}
        self._items_by_category: dict[str, dict[str, dict[str, Any]]] = {
            category: {} for category in self.NAMED_CATEGORIES
        }
        self._sources_by_category: dict[str, dict[str, str]] = {category: {} for category in self.NAMED_CATEGORIES}
        self._field_sources: dict[str, str] = {}
        self._build_root: SourceRoot = get_root_folder()
        self._build_root_locked = False

    def add(self, payload, **kwargs) -> None:
        r"""
        Add a configuration fragment from a dict or a YAML/JSON file.

        Parameters
        ----------
        payload : dict or str or os.PathLike
            Fragment to merge into the current aggregated state.
        source_name : str, optional
            Explicit source label to associate with the fragment.
        use_fast_loader : bool, optional
            Forwarded to the configuration loader.

        Examples
        --------

        .. code-block:: python

            >>> manager.add("tests/config/config_manager_base.yaml")

        .. code-block:: python

            >>> manager.add(
            ...     {
            ...         "facility": "ESRF",
            ...         "machine": "sr",
            ...         "energy": 6e9,
            ...         "data_folder": "/data/store",
            ...         "devices": [],
            ...     }
            ... )
        """
        source_name = kwargs.pop("source_name", None)
        use_fast_loader = kwargs.pop("use_fast_loader", False)
        if kwargs:
            unknown = ", ".join(sorted(kwargs))
            raise PyAMLConfigException(f"Unsupported ConfigurationManager.add() arguments: {unknown}")

        fragment, inferred_source_name, source_root = self._load_payload(
            payload,
            source_name=source_name,
            use_fast_loader=use_fast_loader,
        )
        prepared = self._prepare_fragment(fragment, source_root, inferred_source_name)
        self._merge_fragment(prepared, inferred_source_name)

    def remove(self, category: str, name: str) -> None:
        r"""
        Remove a named entry from an aggregated category.

        Parameters
        ----------
        category : str
            Category that contains the entry.
        name : str
            Entry name to remove.

        Examples
        --------

        .. code-block:: python

            >>> manager.remove("simulators", "tracking")
        """
        self._require_named_category(category)
        if name not in self._items_by_category[category]:
            raise PyAMLConfigException(f"Configuration entry '{name}' not found in category '{category}'.")

        self._state[category] = [entry for entry in self._state.get(category, []) if entry.get("name") != name]
        self._items_by_category[category].pop(name, None)
        self._sources_by_category[category].pop(name, None)

    def replace(self, category: str, element: dict) -> None:
        r"""
        Replace an existing named entry in an aggregated category.

        Parameters
        ----------
        category : str
            Category that contains the entry.
        element : dict
            Replacement configuration entry.

        Examples
        --------

        .. code-block:: python

            >>> manager.replace(
            ...     "simulators",
            ...     {
            ...         "type": "pyaml.lattice.simulator",
            ...         "name": "design",
            ...         "lattice": "tests/config/sr/lattices/ebs.mat",
            ...     },
            ... )
        """
        self._require_named_category(category)
        prepared = self._prepare_fragment(
            {category: [copy.deepcopy(element)]},
            self._build_root,
            f"replace:{category}",
        )
        replacement = prepared[category][0]
        name = replacement["name"]

        if name not in self._items_by_category[category]:
            raise PyAMLConfigException(
                f"Configuration entry '{name}' not found in category '{category}'. Use add() to create it."
            )

        entries = self._state.get(category, [])
        for index, entry in enumerate(entries):
            if entry.get("name") == name:
                entries[index] = replacement
                break

        self._items_by_category[category][name] = replacement
        self._sources_by_category[category][name] = "replace()"

    def clear(self, category: str | None = None) -> None:
        r"""
        Clear the aggregated state, or a single root field/category.

        Parameters
        ----------
        category : str, optional
            If provided, only that category or root field is cleared.

        Examples
        --------

        .. code-block:: python

            >>> manager.clear("simulators")

        .. code-block:: python

            >>> manager.clear()
        """
        if category is None:
            self._state = {"type": self.DEFAULT_TYPE}
            self._field_sources.clear()
            for name in self.NAMED_CATEGORIES:
                self._items_by_category[name].clear()
                self._sources_by_category[name].clear()
            self._build_root = get_root_folder()
            self._build_root_locked = False
            return

        if category in self.NAMED_CATEGORIES:
            self._state[category] = []
            self._items_by_category[category].clear()
            self._sources_by_category[category].clear()
            return

        if category == "type":
            self._state["type"] = self.DEFAULT_TYPE
            self._field_sources.pop("type", None)
            return

        if category in self._state:
            self._state.pop(category, None)
            self._field_sources.pop(category, None)
            return

        raise PyAMLConfigException(f"Unknown configuration category '{category}'.")

    def categories(self) -> list[str]:
        r"""
        Return categories that currently contain entries.

        Returns
        -------
        list[str]

        Examples
        --------

        .. code-block:: python

            >>> manager.categories()
        """
        return [
            category
            for category in self.NAMED_CATEGORIES
            if self._state.get(category) and len(self._state[category]) > 0
        ]

    def keys(self, category: str | None = None) -> list[str]:
        r"""
        Return known entry names.

        Parameters
        ----------
        category : str, optional
            Restrict the result to one category.

        Returns
        -------
        list[str]

        Examples
        --------

        .. code-block:: python

            >>> manager.keys()

        .. code-block:: python

            >>> manager.keys("simulators")
        """
        if category is None:
            names: list[str] = []
            for current_category in self.NAMED_CATEGORIES:
                self._extend_unique(names, self._items_by_category[current_category].keys())
            return names

        self._require_named_category(category)
        return list(self._items_by_category[category].keys())

    def has(self, category: str, name: str) -> bool:
        r"""
        Check whether a named entry exists.

        Parameters
        ----------
        category : str
            Category to inspect.
        name : str
            Entry name.

        Returns
        -------
        bool

        Examples
        --------

        .. code-block:: python

            >>> manager.has("simulators", "design")
            True
        """
        self._require_named_category(category)
        return name in self._items_by_category[category]

    def get(self, category: str, name: str) -> dict[str, Any]:
        r"""
        Return a named configuration entry.

        Parameters
        ----------
        category : str
            Category to inspect.
        name : str
            Entry name.

        Returns
        -------
        dict[str, Any]

        Examples
        --------

        .. code-block:: python

            >>> manager.get("simulators", "design")
        """
        self._require_named_category(category)
        if name not in self._items_by_category[category]:
            raise KeyError(f"Configuration entry '{name}' not found in category '{category}'.")
        return ConfigurationManager.strip_internal_metadata(copy.deepcopy(self._items_by_category[category][name]))

    def find(self, pattern: str, category: str | None = None) -> list[str]:
        r"""
        Search entry names using wildcards or regular expressions.

        Parameters
        ----------
        pattern : str
            Wildcard pattern or regular expression prefixed with ``re:``.
        category : str, optional
            Restrict the search to one category.

        Returns
        -------
        list[str]

        Examples
        --------

        .. code-block:: python

            >>> manager.find("BPM_C04*")

        .. code-block:: python

            >>> manager.find("re:^QF1.*$")
        """
        if not pattern or not pattern.strip():
            raise PyAMLConfigException("Empty configuration query.")

        names = self.keys(category)
        pattern = pattern.strip()
        if pattern.startswith("re:"):
            regex_source = pattern[3:]
            try:
                regex = re.compile(regex_source)
            except re.error as exc:
                raise PyAMLConfigException(f"Invalid regex '{regex_source}': {exc}") from exc
            return [name for name in names if regex.search(name)]

        return [name for name in names if fnmatch.fnmatch(name, pattern)]

    def settings(self) -> dict[str, Any]:
        r"""
        Return aggregated scalar accelerator settings.

        Returns
        -------
        dict[str, Any]

        Examples
        --------

        .. code-block:: python

            >>> manager.settings()
        """
        settings: dict[str, Any] = {}
        ordered_fields = [field for field in self.root_fields() if field in self._state]
        extra_fields = [
            field
            for field in self._state.keys()
            if field not in self.NAMED_CATEGORIES
            and field not in ordered_fields
            and field not in _INTERNAL_METADATA_KEYS
        ]
        for field in ordered_fields + extra_fields:
            settings[field] = copy.deepcopy(self._state[field])
        return ConfigurationManager.strip_internal_metadata(settings)

    def to_dict(self) -> dict[str, Any]:
        r"""
        Return the aggregated configuration as a plain dictionary.

        Returns
        -------
        dict[str, Any]

        Examples
        --------

        .. code-block:: python

            >>> snapshot = manager.to_dict()
        """
        snapshot = self._snapshot(include_internal_metadata=False)
        return snapshot

    def build(self, ignore_external: bool = False):
        r"""
        Build an Accelerator from the aggregated configuration snapshot.

        Parameters
        ----------
        ignore_external : bool, optional
            Forwarded to :meth:`pyaml.accelerator.Accelerator.from_dict`.

        Returns
        -------
        Accelerator

        Examples
        --------

        .. code-block:: python

            >>> sr = manager.build()
        """
        from ..accelerator import Accelerator

        if isinstance(self._build_root, Path):
            set_root_folder(self._build_root)
        snapshot = ConfigurationManager.strip_runtime_internal_metadata(self._snapshot(include_internal_metadata=True))
        return Accelerator.from_dict(snapshot, ignore_external=ignore_external)

    def __dir__(self):
        """
        Extend ``dir()`` with attribute-friendly entry names.

        Examples
        --------

        .. code-block:: python

            >>> "HCORR" in dir(manager)
        """
        default = super().__dir__()
        valid_keys = {key for key in self.keys() if _VALID_QUERY_KEY_RE.match(key)}
        return sorted(set(default) | valid_keys)

    def __getitem__(self, query: str) -> list[str]:
        r"""
        Alias for :meth:`find`.

        Examples
        --------

        .. code-block:: python

            >>> manager["BPM_C04*"]
        """
        return self.find(query)

    def __getattr__(self, name):
        """
        Provide attribute-style access for categories and unambiguous entry names.

        Examples
        --------

        .. code-block:: python

            >>> manager.simulators

        .. code-block:: python

            >>> manager.HCORR
        """
        if name in self._items_by_category:
            return self.keys(name)
        categories = self._categories_for_name(name)
        if len(categories) == 1:
            return self.get(categories[0], name)
        if len(categories) > 1:
            raise AttributeError(
                f"ConfigurationManager key '{name}' is ambiguous across categories {categories}. "
                "Use get(category, name)."
            )
        raise AttributeError(f"'ConfigurationManager' object has no attribute '{name}'")

    def __repr__(self) -> str:
        """
        Return a human-readable overview of the aggregated configuration.

        Examples
        --------

        .. code-block:: python

            >>> repr(manager)
        """
        lines: list[str] = []

        settings = self.settings()
        lines.append("Settings:")
        if settings:
            for key, value in settings.items():
                lines.append(f"    {key}: {value}")
        lines.append("    .")
        lines.append("")

        for category in self.NAMED_CATEGORIES:
            lines.append(f"{_CATEGORY_TITLES[category]}:")
            entries = self._items_by_category[category]
            if entries:
                for entry in self._state.get(category, []):
                    lines.append(self._format_entry(category, entry))
            lines.append("    .")
            lines.append("")

        return "\n".join(lines).rstrip()

    def __str__(self) -> str:
        """
        Return the same overview as :meth:`__repr__`.

        Examples
        --------

        .. code-block:: python

            >>> print(manager)
        """
        return self.__repr__()

    def _load_payload(
        self,
        payload,
        *,
        source_name: str | None,
        use_fast_loader: bool,
    ) -> tuple[dict[str, Any], str, SourceRoot]:
        if isinstance(payload, dict):
            return copy.deepcopy(payload), source_name or "<dict>", None

        payload_path = self._coerce_path(payload)
        if is_remote_url(payload_path):
            fragment, source_root = fetch_remote_config(payload_path, use_fast_loader=use_fast_loader)
            if not self._build_root_locked:
                self._build_root = source_root
                self._build_root_locked = True
            return fragment, source_name or payload_path, source_root

        path = Path(payload_path)
        suffix = path.suffix.lower()
        if suffix not in self._SUPPORTED_FILE_SUFFIXES:
            raise PyAMLConfigException(
                f"Cannot infer configuration source from '{payload_path}'. "
                "Supported inputs are dict, .yaml/.yml files or .json files."
            )

        if not path.exists():
            raise PyAMLConfigException(f"{payload_path} file not found")

        resolved_path = path.resolve()
        previous_root = get_root_folder()
        source_root = resolved_path.parent
        try:
            set_root_folder(source_root)
            fragment = load(resolved_path.name, None, use_fast_loader)
        finally:
            set_root_folder(previous_root)

        if not self._build_root_locked:
            self._build_root = source_root
            self._build_root_locked = True

        return fragment, source_name or str(resolved_path), source_root

    def _prepare_fragment(self, fragment: dict[str, Any], source_root: SourceRoot, source_name: str) -> dict[str, Any]:
        if not isinstance(fragment, dict):
            raise PyAMLConfigException(
                f"ConfigurationManager.add() expects a mapping at the top level, got '{type(fragment).__name__}'."
            )

        accelerator_type = fragment.get("type", self.DEFAULT_TYPE)
        if accelerator_type != self.DEFAULT_TYPE:
            raise UnsupportedConfigurationRootError(
                f"ConfigurationManager only supports '{self.DEFAULT_TYPE}' roots, got '{accelerator_type}'."
            )

        prepared = copy.deepcopy(fragment)
        prepared["type"] = self.DEFAULT_TYPE

        for category in self.NAMED_CATEGORIES:
            if category not in prepared:
                continue

            entries = prepared[category]
            if not isinstance(entries, list):
                raise PyAMLConfigException(f"Configuration category '{category}' must be a list.")

            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    raise PyAMLConfigException(
                        f"Configuration category '{category}' expects object entries, "
                        f"found '{type(entry).__name__}' at index {index} from source '{source_name}'."
                    )
                if "name" not in entry:
                    raise PyAMLConfigException(
                        f"Configuration category '{category}' expects named objects, "
                        f"but entry at index {index} from source '{source_name}' has no 'name'."
                    )
                if "type" not in entry:
                    raise PyAMLConfigException(
                        f"Configuration entry '{entry['name']}' in category '{category}' has no 'type'."
                    )

                if category == "simulators":
                    self._normalize_simulator_paths(entry, entry.get(REMOTE_BASE_URL_KEY, source_root))

        return prepared

    def _merge_fragment(self, fragment: dict[str, Any], source_name: str) -> None:
        duplicate_errors: list[str] = []
        pending_by_category: dict[str, list[dict[str, Any]]] = {}

        for category in self.NAMED_CATEGORIES:
            if category not in fragment:
                continue

            entries = fragment[category]
            seen_in_fragment: dict[str, dict[str, Any]] = {}
            for entry in entries:
                name = entry["name"]
                if name in seen_in_fragment:
                    previous_entry = seen_in_fragment[name]
                    duplicate_errors.append(
                        f"Configuration entry '{name}' is duplicated inside category '{category}'. "
                        f"First declaration: {self._describe_entry_source(previous_entry, source_name)}. "
                        f"Duplicate declaration: {self._describe_entry_source(entry, source_name)}."
                    )
                    continue
                if name in self._items_by_category[category]:
                    previous_entry = self._items_by_category[category][name]
                    previous_source = self._sources_by_category[category].get(name, "<unknown>")
                    duplicate_errors.append(
                        f"Configuration entry '{name}' already exists in category '{category}'. "
                        f"First declaration: {self._describe_entry_source(previous_entry, previous_source)}. "
                        f"Duplicate declaration: {self._describe_entry_source(entry, source_name)}. "
                        "Use replace() to override it."
                    )
                    continue
                seen_in_fragment[name] = entry

            pending_by_category[category] = entries

        if duplicate_errors:
            raise PyAMLConfigException(duplicate_errors[0])

        for field, value in fragment.items():
            if field in self.NAMED_CATEGORIES:
                continue
            self._state[field] = copy.deepcopy(value)
            if field not in _INTERNAL_METADATA_KEYS:
                self._field_sources[field] = source_name

        for category, entries in pending_by_category.items():
            target = self._state.setdefault(category, [])
            for entry in entries:
                copied = copy.deepcopy(entry)
                target.append(copied)
                self._items_by_category[category][copied["name"]] = copied
                self._sources_by_category[category][copied["name"]] = source_name

    def _snapshot(self, *, include_internal_metadata: bool) -> dict[str, Any]:
        snapshot = copy.deepcopy(self._state)
        if include_internal_metadata:
            return snapshot
        return ConfigurationManager.strip_internal_metadata(snapshot)

    def _normalize_simulator_paths(self, entry: dict[str, Any], source_root: SourceRoot) -> None:
        if source_root is None:
            return

        lattice = entry.get("lattice")
        if isinstance(lattice, str) and not os.path.isabs(lattice) and not is_remote_url(lattice):
            entry["lattice"] = resolve_reference(lattice, source_root)

    def _require_named_category(self, category: str) -> None:
        if category not in self.NAMED_CATEGORIES:
            raise PyAMLConfigException(
                f"Unknown configuration category '{category}'. Expected one of: {', '.join(self.NAMED_CATEGORIES)}."
            )

    def _categories_for_name(self, name: str) -> list[str]:
        categories: list[str] = []
        for category in self.NAMED_CATEGORIES:
            if name in self._items_by_category[category]:
                categories.append(category)
        return categories

    def _format_entry(self, category: str, entry: dict[str, Any]) -> str:
        name = entry.get("name", "<unnamed>")
        entry_type = entry.get("type")
        type_part = f" ({entry_type})" if entry_type else ""

        details: list[str] = []
        if category == "catalogs":
            entries = entry.get("entries")
            if isinstance(entries, list):
                details.append(f"entries={len(entries)}")
        if category == "arrays":
            patterns = entry.get("elements")
            if isinstance(patterns, list):
                details.append(f"patterns={len(patterns)}")

        source = self._sources_by_category[category].get(name)
        if source is not None:
            details.append(f"source={self._format_source(source)}")

        detail_part = ""
        if details:
            detail_part = " " + " ".join(details)

        return f"    {name}{type_part}{detail_part}"

    def _format_source(self, source: str) -> str:
        if source.startswith("<") and source.endswith(">"):
            return source
        source_path = Path(source)
        suffix = source_path.suffix.lower()
        if suffix in self._SUPPORTED_FILE_SUFFIXES:
            return source_path.name
        return source

    def _describe_entry_source(self, entry: dict[str, Any], fallback_source: str) -> str:
        location = entry.get("__location__")
        if isinstance(location, tuple) and len(location) == 3:
            source, line, column = location
            return f"source '{source}' at line {line}, column {column}"
        return f"source '{fallback_source}'"

    def _coerce_path(self, payload) -> str:
        if isinstance(payload, (str, os.PathLike)):
            return os.fspath(payload)
        raise PyAMLConfigException(
            f"Cannot infer configuration source from payload of type '{type(payload).__name__}'."
        )

    def _extend_unique(self, target: list[str], values) -> None:
        for value in values:
            if value not in target:
                target.append(value)

    @staticmethod
    def strip_internal_metadata(value):
        """
        Remove additionnal internal informations info from value
        """
        if isinstance(value, list):
            return [ConfigurationManager.strip_internal_metadata(entry) for entry in value]
        if isinstance(value, dict):
            return {
                key: ConfigurationManager.strip_internal_metadata(entry)
                for key, entry in value.items()
                if key not in _INTERNAL_METADATA_KEYS
            }
        return value

    @staticmethod
    def strip_runtime_internal_metadata(value):
        """
        Remove additionnal internal informations info from value
        """
        if isinstance(value, list):
            return [ConfigurationManager.strip_runtime_internal_metadata(entry) for entry in value]
        if isinstance(value, dict):
            return {
                key: ConfigurationManager.strip_runtime_internal_metadata(entry)
                for key, entry in value.items()
                if key != REMOTE_BASE_URL_KEY
            }
        return value
