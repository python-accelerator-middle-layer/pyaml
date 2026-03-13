"""
yellow_pages.py

Fully dynamic YellowPages service attached to Accelerator.

Key points:
- Auto-discovery only: arrays, tools and diagnostics are discovered at runtime
  by scanning all modes.
- No caching: every call reflects current runtime state.
- Simple query syntax for identifiers:
    - wildcard / fnmatch:
        yp["OH4*"]
    - regular expression:
        yp["re:^SH1A-C0[12]-H$"]

Expected Accelerator interface
------------------------------
- controls()   -> dict[str, ElementHolder]
- simulators() -> dict[str, ElementHolder]
- modes()      -> dict[str, ElementHolder]

Expected ElementHolder interface
--------------------------------
- list_arrays() -> set[str]
- list_tools() -> set[str]
- list_diagnostics() -> set[str]
- get_array(name: str) -> Any
- get_tool(name: str) -> Any
- get_diagnostic(name: str) -> Any
"""

from __future__ import annotations

import fnmatch
import re
from enum import Enum
from typing import Any

from pyaml import PyAMLException


class YellowPagesCategory(str, Enum):
    ARRAYS = "Arrays"
    TOOLS = "Tools"
    DIAGNOSTICS = "Diagnostics"


class YellowPagesError(PyAMLException):
    """YellowPages-specific error with clear user-facing messages."""


class YellowPagesQueryError(YellowPagesError):
    """Raised when a YellowPages query string cannot be evaluated."""


_VALID_KEY_RE = re.compile(r"^[A-Z0-9_]+$")


class YellowPages:
    r"""
    Dynamic discovery service for accelerator objects.

    :class:`YellowPages` provides a unified access layer to arrays,
    tuning tools and diagnostics available in an
    :class:`~pyaml.accelerator.Accelerator`.

    Entries are discovered dynamically by scanning all
    :class:`~pyaml.element_holder.ElementHolder` instances
    associated with the accelerator control and simulation modes.

    Notes
    -----
    The :class:`~pyaml.accelerator.Accelerator` must provide:

    - ``controls() -> dict[str, ElementHolder]``
    - ``simulators() -> dict[str, ElementHolder]``
    - ``modes() -> dict[str, ElementHolder]``

    Each :class:`~pyaml.element_holder.ElementHolder` must implement:

    - ``list_arrays()`` / ``get_array(name)``
    - ``list_tools()`` / ``get_tool(name)``
    - ``list_diagnostics()`` / ``get_diagnostic(name)``

    Examples
    --------

    Print the global overview:

    .. code-block:: python

        print(sr.yellow_pages)

    Resolve an entry across all modes:

    .. code-block:: python

        sr.yellow_pages.get("BPM")

    Resolve in a specific mode:

    .. code-block:: python

        sr.yellow_pages.get("BPM", mode="live")

    Search identifiers using wildcards:

    .. code-block:: python

        sr.yellow_pages["OH4*"]

    Search identifiers using a regular expression:

    .. code-block:: python

        sr.yellow_pages["re:^SH1A-C0[12]-H$"]
    """

    def __init__(self, accelerator: Any):
        self._acc = accelerator

    def has(self, key: str) -> bool:
        r"""
        Check whether a YellowPages key exists.

        Parameters
        ----------
        key : str
            Entry name.

        Returns
        -------
        bool
            ``True`` if the key exists.

        Examples
        --------

        .. code-block:: python

            >>> sr.yellow_pages.has("BPM")
            True

        .. code-block:: python

            >>> sr.yellow_pages.has("UNKNOWN")
            False

        """
        return key in self._all_keys()

    def categories(self) -> list[str]:
        r"""
        Return the list of available categories.

        Only categories that contain entries are returned.

        Returns
        -------
        list[str]

        Examples
        --------

        .. code-block:: python

            >>> sr.yellow_pages.categories()
            ['Arrays', 'Tools', 'Diagnostics']

        """
        discovered = self._discover()
        present = {cat for cat, keys in discovered.items() if keys}
        return [c.value for c in YellowPagesCategory if c in present]

    def keys(self, category: str | YellowPagesCategory | None = None) -> list[str]:
        r"""
        Return available YellowPages keys.

        Parameters
        ----------
        category : str or YellowPagesCategory, optional
            Restrict the result to a specific category.

        Returns
        -------
        list[str]

        Examples
        --------

        All entries:

        .. code-block:: python

            >>> sr.yellow_pages.keys()

        Only arrays:

        .. code-block:: python

            >>> sr.yellow_pages.keys("Arrays")

        Using enum:

        .. code-block:: python

            >>> sr.yellow_pages.keys(YellowPagesCategory.ARRAYS)

        """
        discovered = self._discover()

        if category is None:
            return self._all_keys()

        cat = YellowPagesCategory(category)
        return discovered.get(cat, [])

    def __dir__(self):
        """
        Extend ``dir()`` with attribute-friendly discovered keys.
        """
        default = super().__dir__()
        return sorted(set(default) | {k for k in self._all_keys() if _VALID_KEY_RE.match(k)})

    def __getattr__(self, name):
        """
        Allow attribute-style access for valid discovered keys.

        Examples
        --------

        .. code-block:: python

            sr.yellow_pages.BPM
        """
        if name in self._all_keys():
            return self._get_object(name)
        raise AttributeError(f"'YellowPages' object has no attribute '{name}'")

    def availability(self, key: str) -> set[str]:
        r"""
        Return the set of modes where a key is available.

        Parameters
        ----------
        key : str
            Entry name.

        Returns
        -------
        set[str]

        Examples
        --------

        .. code-block:: python

            sr.yellow_pages.availability("BPM")
            sr.yellow_pages.availability("DEFAULT_ORBIT_CORRECTION")
        """
        self._require_key(key)
        avail: set[str] = set()
        for mode_name, holder in self._acc.modes().items():
            if self._try_resolve_in_holder(key, holder) is not None:
                avail.add(mode_name)
        return avail

    def _get_object(self, key: str, *, mode: str | None = None):
        r"""
        Resolve a YellowPages entry.

        Parameters
        ----------
        key : str
            Entry name.
        mode : str, optional
            Restrict the resolution to a specific mode.

        Returns
        -------
        object or dict[str, object]

            If ``mode`` is specified, returns the resolved object.

            Otherwise returns a dictionary mapping mode names
            to resolved objects.

        Raises
        ------
        KeyError
            If the key does not exist.
        YellowPagesError
            If the mode is unknown or the key is not available
            in the requested mode.

        Examples
        --------

        Resolve across all modes:

        .. code-block:: python

            >>> sr.yellow_pages.get("BPM")

        Resolve in a specific mode:

        .. code-block:: python

            >>> sr.yellow_pages.get("BPM", mode="live")

        Using attribute access:

        .. code-block:: python

            >>> sr.yellow_pages.BPM

        """
        self._require_key(key)

        if mode is not None:
            holder = self._acc.modes().get(mode)
            if holder is None:
                raise YellowPagesError(f"Unknown mode '{mode}'.")
            obj = self._try_resolve_in_holder(key, holder)
            if obj is None:
                raise YellowPagesError(f"YellowPages key '{key}' not available in mode '{mode}'.")
            return obj

        out: dict[str, Any] = {}
        for mode_name, holder in self._acc.modes().items():
            obj = self._try_resolve_in_holder(key, holder)
            if obj is not None:
                out[mode_name] = obj
        return out

    def __getitem__(self, query: str) -> list[str]:
        """
        Alias for :meth:`get`.
        """
        return self.get(query)

    def get(self, query: str, mode: str | None = None) -> list[str]:
        """
        Search identifiers using a wildcard or regular expression.

        Parameters
        ----------
        query : str
            Search expression.
        mode : str, optional
            Restrict the search to a specific accelerator mode.

        Returns
        -------
        list[str]

        Examples
        --------

        .. code-block:: python

            >>> sr.yellow_pages.get("OH4*")

            >>> sr.yellow_pages.get("OH4*", mode="live")

            >>> sr.yellow_pages.get("re:^SH1A-C0[12]-H$")

        """
        if not query or not query.strip():
            raise YellowPagesQueryError("Empty YellowPages query.")

        query = query.strip()

        if mode is not None:
            holder = self._acc.modes().get(mode)
            if holder is None:
                raise YellowPagesError(f"Unknown mode '{mode}'.")

            if query in holder.list_arrays():
                return self._object_to_ids(holder.get_array(query))
            else:
                ids = self._ids_from_holder(holder)
        else:
            if query in self.keys(YellowPagesCategory.ARRAYS):
                if mode is None:
                    arr_list: list[str] = []
                    for a_mode in self._acc.modes():
                        try:
                            obj = self._get_object(query, mode=a_mode)
                            array_ids = self._object_to_ids(obj)
                            self._extend_unique(arr_list, array_ids)
                        except Exception:
                            continue
                    return arr_list

                return self._object_to_ids(self._get_object(query, mode=mode))
            ids = self._all_known_ids()

        if query.startswith("re:"):
            pattern = query[3:]
            try:
                rx = re.compile(pattern)
            except re.error as ex:
                raise YellowPagesQueryError(f"Invalid regex '{pattern}': {ex}") from ex

            return [i for i in ids if rx.search(i)]

        return [i for i in ids if fnmatch.fnmatch(i, query)]

    def __repr__(self) -> str:
        r"""
        Return a human-readable overview of the YellowPages content.

        The representation lists:

        - controls
        - simulators
        - discovered arrays, tools and diagnostics

        The displayed type corresponds to the Python module
        defining the resolved object.

        Examples
        --------

        .. code-block:: python

            print(sr.yellow_pages)

        Example output:

        .. code-block:: text

            Controls:
                live
                .

            Simulators:
                design
                .

            Arrays:
                BPM (pyaml.arrays.bpm_array) size=224
                HCORR (pyaml.arrays.magnet_array) size=96
                .

            Tools:
                DEFAULT_ORBIT_CORRECTION (pyaml.tuning_tools.orbit)
                .

            Diagnostics:
                BETATRON_TUNE (pyaml.diagnostics.tune_monitor)
                .
        """
        lines: list[str] = []

        lines.append("Controls:")
        controls = self._acc.controls()
        if controls:
            for name in controls.keys():
                lines.append(f"    {name}")
        lines.append("    .")
        lines.append("")

        lines.append("Simulators:")
        simulators = self._acc.simulators()
        if simulators:
            for name in simulators.keys():
                lines.append(f"    {name}")
        lines.append("    .")
        lines.append("")

        discovered = self._discover()
        for cat in YellowPagesCategory:
            keys = discovered.get(cat, set())
            if not keys:
                continue

            lines.append(f"{cat.value}:")
            for key in keys:
                lines.append(self._format_key(cat, key))
            lines.append("    .")
            lines.append("")

        return "\n".join(lines).rstrip()

    def __str__(self) -> str:
        return self.__repr__()

    def _discover(self) -> dict[YellowPagesCategory, list[str]]:
        arrays: list[str] = []
        tools: list[str] = []
        diags: list[str] = []

        for _, holder in self._acc.modes().items():
            try:
                self._extend_unique(arrays, holder.list_arrays())
            except Exception:
                pass
            try:
                self._extend_unique(tools, holder.list_tools())
            except Exception:
                pass
            try:
                self._extend_unique(diags, holder.list_diagnostics())
            except Exception:
                pass

        return {
            YellowPagesCategory.ARRAYS: arrays,
            YellowPagesCategory.TOOLS: tools,
            YellowPagesCategory.DIAGNOSTICS: diags,
        }

    def _extend_unique(self, target: list[str], values: list[str]) -> None:
        """
        Append values to target while preserving insertion order and uniqueness.
        """
        for value in values:
            if value not in target:
                target.append(value)

    def _all_keys(self) -> list[str]:
        discovered = self._discover()
        out: list[str] = []
        for keys in discovered.values():
            self._extend_unique(out, keys)
        return out

    def _require_key(self, key: str) -> None:
        if key not in self._all_keys():
            raise KeyError(self._unknown_key_message(key))

    def _unknown_key_message(self, key: str) -> str:
        available = ", ".join(self._all_keys())
        return f"Unknown YellowPages key '{key}'. Available keys: {available if available else '<none>'}"

    def _try_resolve_in_holder(self, key: str, holder: Any) -> Any | None:
        """
        Resolve a discovered key in a holder.

        Resolution order:
        - arrays
        - tools
        - diagnostics
        """
        try:
            if key in holder.list_arrays():
                return holder.get_array(key)
        except Exception:
            pass

        try:
            if key in holder.list_tools():
                return holder.get_tool(key)
        except Exception:
            pass

        try:
            if key in holder.list_diagnostics():
                return holder.get_diagnostic(key)
        except Exception:
            pass

        return None

    def _get_type_name_from_resolved(self, resolved: dict[str, Any]) -> str | None:
        """
        Return the public type name used in ``__repr__``.

        Only the module path is displayed, not the concrete class name.

        Examples
        --------

        .. code-block:: text

            pyaml.arrays.bpm_array
            pyaml.tuning_tools.orbit
            pyaml.diagnostics.tune_monitor
        """
        for obj in resolved.values():
            if obj is None:
                continue
            return obj.__class__.__module__
        return None

    def _format_key(self, category: YellowPagesCategory, key: str) -> str:
        """
        Format one discovered key for ``__repr__``.
        """
        resolved = self._get_object(key)
        type_name = self._get_type_name_from_resolved(resolved)
        type_part = f" ({type_name})" if type_name else ""

        modes = list(resolved.keys())
        all_modes = list(self._acc.modes().keys())

        availability_part = ""
        if set(modes) != set(all_modes):
            missing = [mode for mode in all_modes if mode not in modes]
            availability_part = f" modes={modes} missing={missing}"

        if category == YellowPagesCategory.ARRAYS:
            sizes: dict[str, int] = {}
            for mode_name, obj in resolved.items():
                try:
                    sizes[mode_name] = len(obj)
                except Exception:
                    sizes[mode_name] = 0

            if modes == all_modes and sizes and len(set(sizes.values())) == 1:
                size_part = f" size={next(iter(sizes.values()))}"
            else:
                size_part = " size={" + ", ".join(f"{m}:{n}" for m, n in sizes.items()) + "}"

            return f"    {key:<21}{type_part:<40}{size_part}{availability_part}"

        return f"    {key}{type_part}{availability_part}"

    def _object_to_ids(self, obj: Any) -> list[str]:
        """
        Convert a resolved object into a set of identifiers.
        """
        if obj is None:
            return []

        if isinstance(obj, (list, tuple, set)) and all(isinstance(x, str) for x in obj):
            return list(obj)

        ids: list[str] = list()
        try:
            for x in obj:
                if isinstance(x, str):
                    if x not in ids:
                        ids.append(x)
                elif hasattr(x, "get_name") and callable(x.get_name):
                    if x.get_name() not in ids:
                        ids.append(x.get_name())
                elif hasattr(x, "name") and callable(x.name):
                    if x.name() not in ids:
                        ids.append(x.name())
                elif hasattr(x, "name") and isinstance(x.name, str):
                    if x.name not in ids:
                        ids.append(x.name)
                else:
                    if str(x) not in ids:
                        ids.append(str(x))
            return ids
        except TypeError:
            if isinstance(obj, str):
                return [obj]
            if hasattr(obj, "get_name") and callable(obj.get_name):
                return [obj.get_name()]
            return [str(obj)]

    def _ids_for_key_union_all_modes(self, key: str) -> list[str]:
        out: list[str] = []
        resolved = self._get_object(key)
        for obj in resolved.values():
            self._extend_unique(out, self._object_to_ids(obj))
        return out

    def _all_known_ids(self) -> list[str]:
        """
        Collect all identifiers from all discovered arrays across all modes.
        """
        all_ids: list[str] = []
        for array_name in self.keys(YellowPagesCategory.ARRAYS):
            try:
                self._extend_unique(all_ids, self._ids_for_key_union_all_modes(array_name))
            except Exception:
                continue
        return all_ids

    def _ids_from_holder(self, holder) -> list[str]:
        ids: list[str] = []

        try:
            for name in holder.list_arrays():
                arr = holder.get_array(name)
                self._extend_unique(ids, self._object_to_ids(arr))
        except Exception:
            pass

        return ids
