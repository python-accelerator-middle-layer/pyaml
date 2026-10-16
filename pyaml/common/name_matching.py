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
        ``re:``. Prefix any of those with ``~`` to exclude its matches
        instead of including them, mirroring the ``elements:`` selector list
        convention used in YAML configuration. A sequence of patterns is
        resolved entry by entry: non-``~`` entries are unioned,
        de-duplicated, in first-encounter order, then anything matched by a
        ``~`` entry is removed from that union. If every entry is
        ``~``-prefixed (including a single lone ``~pattern``, treated as a
        one-entry sequence), there is no explicit inclusion, so the base set
        defaults to the full pool: ``~pattern`` alone means "everything
        except pattern".

    Returns
    -------
    list[str]
        Matching names.

    Raises
    ------
    PyAMLException
        If a literal pattern (or the remainder of a ``~``-prefixed one) does
        not match any name in `pool`, or if a `re:`-prefixed pattern is not
        a valid regular expression.
    """
    names = list(pool)
    patterns = pattern if isinstance(pattern, (list, tuple)) else [pattern]

    included: list[str] = []
    seen: set[str] = set()
    excluded: set[str] = set()
    has_inclusion = False
    for p in patterns:
        if p.startswith("~"):
            excluded.update(_resolve_one(names, p[1:], what))
            continue
        has_inclusion = True
        for name in _resolve_one(names, p, what):
            if name not in seen:
                seen.add(name)
                included.append(name)

    base = included if has_inclusion else names
    return [n for n in base if n not in excluded]


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
