"""
yellow_pages.py

Fully dynamic YellowPages service attached to Accelerator.

Key points:
- Auto-discovery ONLY: arrays/tools/diagnostics are discovered at runtime by scanning
  all modes.
- No caching: every call reflects current runtime state.

Expected Accelerator interface:
- controls()   -> dict[str, ElementHolder]
- simulators() -> dict[str, ElementHolder]
- modes()      -> dict[str, ElementHolder]   (union of controls + simulators)

Expected ElementHolder interface:
- list_arrays()      -> set[str]
- list_tools()       -> set[str]
- list_diagnostics() -> set[str]
- get_array(name: str)      -> Any
- get_tool(name: str)       -> Any
- get_diagnostic(name: str) -> Any

Query language via __getitem__:
- Operands:
  - KEY: discovered identifier (e.g. BPM, HCORR, VCORR)
  - Regex: use re{ ... } (recommended) or re:... (legacy simple form)

- Operators:
  - Union:        |
  - Intersection: &
  - Difference:   -
  - Parentheses:  ( )

Regex grammar:
- Preferred form: re{<python-regex>}
  - Allows '-', parentheses, spaces, etc.
  - Escape '}' as '\\}' inside the regex.

Examples
--------
>>> yp["BPM"]
>>> yp["HCORR|VCORR"]
>>> yp["BPM - re{BPM_C01-01}"]
>>> yp["re{^BPM_C..-..$}"]
>>> yp["(HCORR|VCORR) - re{CH_.*}"]

Notes
-----
- KEY operands in queries are treated as arrays and converted to IDs.
- Regex operands filter over ALL known IDs gathered from all discovered arrays across
  all modes.
"""

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
    """Raised when a YellowPages query string cannot be parsed/evaluated."""


_VALID_KEY_RE = re.compile(r"^[A-Z0-9_]+$")


# ---------------------------
# Query parsing helpers
# ---------------------------

# Regex operand supports:
# - re{...} where ... may include operators chars like '-', '|', '&', parentheses,
#   spaces, etc.
#   '}' can be escaped as '\}' inside.
#
# We match: re{ (?: \\. | [^}] )* }
# meaning: either an escaped char (e.g. '\}') or any char except '}'.
_TOKEN_RE = re.compile(
    r"""
    \s*(
        re\{(?:\\.|[^}])*\}     |  # regex token with braces, supports escaped chars
        re:[^\s\|\&\-\(\)]+     |  # legacy regex token (no spaces/operators/parens)
        [A-Z0-9_]+              |  # identifier token (YellowPages key)
        \|\|?                   |  # '|' or '||'
        \&\&?                   |  # '&' or '&&'
        \-                      |  # difference
        \(|\)                      # parentheses
    )\s*
    """,
    re.VERBOSE,
)


def _tokenize(expr: str) -> list[str]:
    if not expr or not expr.strip():
        raise YellowPagesQueryError("Empty YellowPages query.")

    pos = 0
    tokens: list[str] = []
    while pos < len(expr):
        m = _TOKEN_RE.match(expr, pos)
        if not m:
            snippet = expr[pos : min(len(expr), pos + 32)]
            raise YellowPagesQueryError(f"Cannot tokenize near: '{snippet}'")
        tok = m.group(1)
        if tok == "||":
            tok = "|"
        if tok == "&&":
            tok = "&"
        tokens.append(tok)
        pos = m.end()
    return tokens


def _to_rpn(tokens: list[str]) -> list[str]:
    """
    Shunting-yard to RPN.

    Precedence:
    - '&' and '-' higher than '|'
    - all left-associative
    """
    prec = {"|": 1, "&": 2, "-": 2}
    output: list[str] = []
    stack: list[str] = []

    for tok in tokens:
        if tok == "(":
            stack.append(tok)
        elif tok == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack or stack[-1] != "(":
                raise YellowPagesQueryError("Mismatched parentheses.")
            stack.pop()
        elif tok in prec:
            while stack and stack[-1] in prec and prec[stack[-1]] >= prec[tok]:
                output.append(stack.pop())
            stack.append(tok)
        else:
            output.append(tok)

    while stack:
        if stack[-1] in ("(", ")"):
            raise YellowPagesQueryError("Mismatched parentheses.")
        output.append(stack.pop())

    return output


def _extract_regex(tok: str) -> str:
    """
    Extract regex pattern from a regex token.

    Supported:
    - re{...} (preferred)
    - re:...  (legacy)
    """
    if tok.startswith("re{") and tok.endswith("}"):
        inner = tok[3:-1]
        # Interpret escaped sequences (e.g. '\}' -> '}')
        # Keep it simple: only unescape '\}' and '\\'
        inner = inner.replace(r"\}", "}").replace(r"\\", "\\")
        return inner

    if tok.startswith("re:"):
        return tok[3:]

    raise YellowPagesQueryError(f"Invalid regex token '{tok}'")


# ---------------------------
# YellowPages service (full dynamic)
# ---------------------------


class YellowPages:
    """
    Fully dynamic YellowPages service attached to Accelerator.

    Discovery:
    - keys/categories are derived by scanning all modes at runtime.

    Resolution:
    - get(key, mode="...") resolves in a specific mode.
    - get(key) returns dict[mode_name, obj] for all modes where available.

    Query language (arrays/IDs):
    - yp["BPM"]
    - yp["HCORR|VCORR"]
    - yp["BPM - re{BPM_C01-01}"]
    """

    def __init__(self, accelerator: Any):
        self._acc = accelerator

    # ---------------------------
    # Discovery API
    # ---------------------------

    def has(self, key: str) -> bool:
        return key in self._all_keys()

    def categories(self) -> list[str]:
        discovered = self._discover()
        present = {cat for cat, keys in discovered.items() if keys}
        return [c.value for c in YellowPagesCategory if c in present]

    def keys(self, category: str | YellowPagesCategory | None = None) -> list[str]:
        discovered = self._discover()

        if category is None:
            return sorted(self._all_keys())

        cat = YellowPagesCategory(category)
        return sorted(discovered.get(cat, set()))

    # ---------------------------
    # Bonus: REPL-friendly exploration
    # ---------------------------

    def __dir__(self):
        default = super().__dir__()
        return sorted(
            set(default) | {k for k in self._all_keys() if _VALID_KEY_RE.match(k)}
        )

    def __getattr__(self, name):
        if name in self._all_keys():
            return self.get(name)
        raise AttributeError(f"'YellowPages' object has no attribute '{name}'")

    # ---------------------------
    # Resolution API
    # ---------------------------

    def availability(self, key: str) -> set[str]:
        self._require_key(key)
        avail: set[str] = set()
        for mode_name, holder in self._acc.modes().items():
            if self._try_resolve_in_holder(key, holder) is not None:
                avail.add(mode_name)
        return avail

    def get(self, key: str, *, mode: str | None = None):
        self._require_key(key)

        if mode is not None:
            holder = self._acc.modes().get(mode)
            if holder is None:
                raise YellowPagesError(f"Unknown mode '{mode}'.")
            obj = self._try_resolve_in_holder(key, holder)
            if obj is None:
                raise YellowPagesError(
                    f"YellowPages key '{key}' not available in mode '{mode}'."
                )
            return obj

        out: dict[str, Any] = {}
        for mode_name, holder in self._acc.modes().items():
            obj = self._try_resolve_in_holder(key, holder)
            if obj is not None:
                out[mode_name] = obj
        return out

    # ---------------------------
    # Query language: yp["..."]  (arrays/IDs only)
    # ---------------------------

    def __getitem__(self, query: str) -> list[str]:
        ids = self._eval_query_to_ids(query)
        return sorted(ids)

    # ---------------------------
    # Printing / introspection
    # ---------------------------

    def __repr__(self) -> str:
        lines: list[str] = []

        lines.append("Controls:")
        controls = self._acc.controls()
        if controls:
            for name in sorted(controls.keys()):
                lines.append(f"    {name}")
        lines.append("    .")
        lines.append("")

        lines.append("Simulators:")
        simulators = self._acc.simulators()
        if simulators:
            for name in sorted(simulators.keys()):
                lines.append(f"    {name}")
        lines.append("    .")
        lines.append("")

        discovered = self._discover()
        for cat in YellowPagesCategory:
            keys = discovered.get(cat, set())
            if not keys:
                continue

            lines.append(f"{cat.value}:")
            for key in sorted(keys):
                lines.append(self._format_key(cat, key))
            lines.append("    .")
            lines.append("")

        return "\n".join(lines).rstrip()

    def __str__(self) -> str:
        return self.__repr__()

    # ---------------------------
    # Internals: discovery
    # ---------------------------

    def _discover(self) -> dict[YellowPagesCategory, set[str]]:
        arrays: set[str] = set()
        tools: set[str] = set()
        diags: set[str] = set()

        for _, holder in self._acc.modes().items():
            try:
                arrays |= set(holder.list_arrays())
            except Exception:
                pass
            try:
                tools |= set(holder.list_tools())
            except Exception:
                pass
            try:
                diags |= set(holder.list_diagnostics())
            except Exception:
                pass

        return {
            YellowPagesCategory.ARRAYS: arrays,
            YellowPagesCategory.TOOLS: tools,
            YellowPagesCategory.DIAGNOSTICS: diags,
        }

    def _all_keys(self) -> set[str]:
        discovered = self._discover()
        out: set[str] = set()
        for keys in discovered.values():
            out |= set(keys)
        return out

    # ---------------------------
    # Internals: resolution
    # ---------------------------

    def _require_key(self, key: str) -> None:
        if key not in self._all_keys():
            raise KeyError(self._unknown_key_message(key))

    def _unknown_key_message(self, key: str) -> str:
        available = ", ".join(sorted(self._all_keys()))
        return (
            f"Unknown YellowPages key '{key}'. "
            f"Available keys: {available if available else '<none>'}"
        )

    def _try_resolve_in_holder(self, key: str, holder: Any) -> Any | None:
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

    # ---------------------------
    # Internals: repr formatting
    # ---------------------------

    def _get_type_name(self, key: str) -> str | None:
        """
        Determine the fully qualified type name of a YellowPages entry.

        The type is inferred from the first resolved object found across modes.
        """
        resolved = self.get(key)

        for obj in resolved.values():
            if obj is None:
                continue

            cls = obj.__class__
            return f"{cls.__module__}.{cls.__name__}"

        return None

    def _format_key(self, category: YellowPagesCategory, key: str) -> str:
        type_name = self._get_type_name(key)
        type_part = f" ({type_name})" if type_name else ""
        resolved = self.get(key)  # dict[mode,obj] where available
        modes = sorted(resolved.keys())
        all_modes = sorted(self._acc.modes().keys())

        availability_part = ""
        if set(modes) != set(all_modes):
            missing = sorted(set(all_modes) - set(modes))
            availability_part = f" modes={modes} missing={missing}"

        if category == YellowPagesCategory.ARRAYS:
            sizes: dict[str, int] = {}
            for mode_name, obj in resolved.items():
                try:
                    sizes[mode_name] = len(obj)
                except Exception:
                    sizes[mode_name] = 0

            if set(modes) == set(all_modes) and sizes and len(set(sizes.values())) == 1:
                size_part = f" size={next(iter(sizes.values()))}"
            else:
                size_part = (
                    " size={"
                    + ", ".join(f"{m}:{n}" for m, n in sorted(sizes.items()))
                    + "}"
                )

            return f"    {key:<10}{type_part:<40}{size_part}{availability_part}"

        return f"    {key}{type_part}{availability_part}"

    # ---------------------------
    # Internals: ID extraction
    # ---------------------------

    def _object_to_ids(self, obj: Any) -> set[str]:
        if obj is None:
            return set()

        if isinstance(obj, (list, tuple, set)) and all(isinstance(x, str) for x in obj):
            return set(obj)

        ids: set[str] = set()
        try:
            for x in obj:
                if isinstance(x, str):
                    ids.add(x)
                elif hasattr(x, "get_name") and callable(x.get_name):
                    ids.add(x.get_name())
                elif hasattr(x, "name") and callable(x.name):
                    ids.add(x.name())
                elif hasattr(x, "name") and isinstance(x.name, str):
                    ids.add(x.name)
                else:
                    ids.add(str(x))
            return ids
        except TypeError:
            if isinstance(obj, str):
                return {obj}
            if hasattr(obj, "get_name") and callable(obj.get_name):
                return {obj.get_name()}
            return {str(obj)}

    def _ids_for_key_union_all_modes(self, key: str) -> set[str]:
        out: set[str] = set()
        resolved = self.get(key)  # dict[mode,obj]
        for obj in resolved.values():
            out |= self._object_to_ids(obj)
        return out

    def _all_known_ids(self) -> set[str]:
        all_ids: set[str] = set()
        for array_name in self.keys(YellowPagesCategory.ARRAYS):
            try:
                all_ids |= self._ids_for_key_union_all_modes(array_name)
            except Exception:
                continue
        return all_ids

    # ---------------------------
    # Query evaluation
    # ---------------------------

    def _eval_query_to_ids(self, expr: str) -> set[str]:
        tokens = _tokenize(expr)
        rpn = _to_rpn(tokens)

        stack: list[set[str]] = []
        for tok in rpn:
            if tok in ("|", "&", "-"):
                if len(stack) < 2:
                    raise YellowPagesQueryError(
                        f"Missing operand for operator '{tok}'."
                    )
                b = stack.pop()
                a = stack.pop()
                if tok == "|":
                    stack.append(a | b)
                elif tok == "&":
                    stack.append(a & b)
                else:
                    stack.append(a - b)
                continue

            # Regex operand (preferred re{...} or legacy re:...)
            if tok.startswith("re{") or tok.startswith("re:"):
                pattern = _extract_regex(tok)
                try:
                    rx = re.compile(pattern)
                except re.error as ex:
                    raise YellowPagesQueryError(
                        f"Invalid regex '{pattern}': {ex}"
                    ) from ex

                base = self._all_known_ids()
                stack.append({i for i in base if rx.search(i)})
                continue

            # KEY operand
            if tok not in self._all_keys():
                raise YellowPagesQueryError(self._unknown_key_message(tok))

            stack.append(self._ids_for_key_union_all_modes(tok))

        if len(stack) != 1:
            raise YellowPagesQueryError("Invalid expression (remaining operands).")

        return stack[0]
