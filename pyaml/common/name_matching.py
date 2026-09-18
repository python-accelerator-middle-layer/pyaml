"""Shared name and wildcard resolution convention used by every holder and array."""

import fnmatch
import re
from typing import Iterable

from .exception import PyAMLException

WILDCARD_CHARS = frozenset("*?[")


def is_wildcard(pattern: str) -> bool:
    """Return True if `pattern` contains an fnmatch wildcard character."""
    return any(c in pattern for c in WILDCARD_CHARS)


def resolve_names(pool: Iterable[str], pattern: str | list[str] | tuple[str, ...], what: str = "Element") -> list[str]:
    """
    Resolve one pattern, or several, against a pool of names.

    Parameters
    ----------
    pool : Iterable[str]
        Names to match against.
    pattern : str, list[str] or tuple[str, ...]
        A literal name, an fnmatch wildcard (triggered by ``*``, ``?`` or
        ``[`` anywhere in the string), or a regular expression prefixed with
        ``re:``. A sequence of patterns is resolved entry by entry and the
        results are unioned, de-duplicated, in first-encounter order.

    Returns
    -------
    list[str]
        Matching names.

    Raises
    ------
    PyAMLException
        If a literal pattern does not match any name in `pool`, or if a
        `re:`-prefixed pattern is not a valid regular expression.
    """
    names = list(pool)
    patterns = pattern if isinstance(pattern, (list, tuple)) else [pattern]

    resolved: list[str] = []
    seen: set[str] = set()
    for p in patterns:
        for name in _resolve_one(names, p, what):
            if name not in seen:
                seen.add(name)
                resolved.append(name)
    return resolved


def _resolve_one(names: list[str], pattern: str, what: str) -> list[str]:
    if pattern.startswith("re:"):
        source = pattern[3:]
        try:
            compiled = re.compile(source)
        except re.error as exc:
            raise PyAMLException(f"Invalid regex '{source}': {exc}") from exc
        return [n for n in names if compiled.fullmatch(n)]
    if is_wildcard(pattern):
        return [n for n in names if fnmatch.fnmatchcase(n, pattern)]
    if pattern not in names:
        raise PyAMLException(f"{what} {pattern} not defined")
    return [pattern]
