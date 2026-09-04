"""Fetch and expand configuration documents from HTTP(S) sources.

The helpers in this module download YAML or JSON documents, resolve relative
remote includes, expand path references, and detect circular inclusions.
"""

import io
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import ProxyHandler, build_opener

import yaml
from yaml import CLoader

from ..common.exception import PyAMLConfigException
from .fileloader import ACCEPTED_SUFFIXES, SafeLineLoader

REMOTE_BASE_URL_KEY = "__baseurl__"
SourceRoot = Path | str | None
_REMOTE_SCHEMES = {"http", "https"}

FILE_PREFIX = "${path:"


class _NamedStringIO(io.StringIO):
    """In-memory text stream that preserves a source name for YAML errors.

    Parameters
    ----------
        value : str
            Text content exposed by the stream.
        name : str
            Source name retained for parser diagnostics.
    """

    def __init__(self, value: str, name: str):
        """
        Initialize the _NamedStringIO.

        Parameters
        ----------
        value : str
            Document text exposed by the stream.
        name : str
            Source name associated with the document.
        """
        super().__init__(value)
        self.name = name


def is_remote_url(value: str) -> bool:
    """Return whether a string uses the HTTP or HTTPS URL scheme.

    Parameters
    ----------
    value : str
        Value to inspect.

    Returns
    -------
    bool
        ``True`` for HTTP(S) URLs; otherwise ``False``.
    """
    return urlparse(value).scheme in _REMOTE_SCHEMES


def fetch_remote_config(url: str, *, include_locations: bool = True) -> tuple[dict[str, Any] | list[Any], str]:
    """Fetch, parse, and expand a remote configuration document.

    Parameters
    ----------
    url : str
        HTTP(S) URL of the YAML or JSON document.
    include_locations : bool
        Preserve source locations in YAML mappings when ``True``.

    Returns
    -------
    tuple[dict[str, Any] | list[Any], str]
        Expanded document and its base URL for resolving relative includes.
    """
    normalized_url = _normalize_remote_url(url)
    expanded = _load_remote_document(normalized_url, include_locations=include_locations, stack=[])
    return expanded, _remote_base_url(normalized_url)


def resolve_reference(reference: str, source_root: SourceRoot) -> str:
    """Resolve a local or remote configuration reference.

    Parameters
    ----------
    reference : str
        Path or URL reference to resolve.
    source_root : SourceRoot
        Local directory or remote base URL used for relative references.

    Returns
    -------
    str
        Absolute local path, resolved remote URL, or unchanged reference.
    """
    if is_remote_url(reference) or os.path.isabs(reference):
        return reference

    if isinstance(source_root, Path):
        return str((source_root / reference).resolve())

    if isinstance(source_root, str):
        return urljoin(source_root, reference)

    return reference


def _normalize_remote_url(url: str) -> str:
    """Validate that a configuration source is an HTTP(S) URL.

    Parameters
    ----------
    url : str
        URL to validate.

    Returns
    -------
    str
        The validated URL.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _REMOTE_SCHEMES:
        raise PyAMLConfigException(f"Unsupported remote configuration source '{url}'.")
    return url


def _load_remote_document(
    url: str,
    *,
    include_locations: bool,
    stack: list[str],
) -> dict[str, Any] | list[Any]:
    """Download, parse, and recursively expand one remote document.

    Parameters
    ----------
    url : str
        URL of the document to load.
    include_locations : bool
        Preserve YAML source locations when ``True``.
    stack : list[str]
        URLs currently being loaded, used for cycle detection.

    Returns
    -------
    dict[str, Any] | list[Any]
        Parsed and recursively expanded document.
    """
    if url in stack:
        raise PyAMLConfigException(f"Circular remote configuration inclusion detected for '{url}'.")

    payload, content_type = _download_text(url)
    document = _parse_remote_document(url, payload, content_type, include_locations=include_locations)
    return _expand_remote_value(document, _remote_base_url(url), stack + [url], include_locations=include_locations)


def _download_text(url: str) -> tuple[str, str]:
    """Download a remote document and return its text and media type.

    Parameters
    ----------
    url : str
        HTTP(S) URL to request.

    Returns
    -------
    tuple[str, str]
        Document text and response content type.
    """
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(url, timeout=10) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            content_type = response.headers.get_content_type()
            body = response.read().decode(charset)
            return body, content_type
    except HTTPError as ex:
        raise PyAMLConfigException(f"Unable to fetch remote configuration '{url}': HTTP {ex.code}.") from ex
    except URLError as ex:
        raise PyAMLConfigException(f"Unable to fetch remote configuration '{url}': {ex.reason}.") from ex
    except OSError as ex:
        raise PyAMLConfigException(f"Unable to fetch remote configuration '{url}': {ex}.") from ex


def _parse_remote_document(
    url: str,
    payload: str,
    content_type: str,
    *,
    include_locations: bool,
) -> dict[str, Any] | list[Any]:
    """Parse downloaded JSON or YAML text into Python objects.

    Parameters
    ----------
    url : str
        Source URL, used for format detection and error messages.
    payload : str
        Downloaded document text.
    content_type : str
        HTTP response media type.
    include_locations : bool
        Preserve source locations in YAML mappings when ``True``.

    Returns
    -------
    dict[str, Any] | list[Any]
        Parsed mapping or sequence.
    """
    suffix = Path(urlparse(url).path).suffix.lower()

    if content_type == "application/json" or suffix == ".json":
        try:
            return json.loads(payload)
        except json.JSONDecodeError as ex:
            raise PyAMLConfigException(f"{url}: {ex}") from ex

    loader = CLoader if not include_locations else SafeLineLoader
    try:
        stream = _NamedStringIO(payload, url)
        return yaml.load(stream, Loader=loader)
    except yaml.YAMLError as ex:
        raise PyAMLConfigException(f"{url}: {ex}") from ex


def _expand_remote_value(value, base_url: str, stack: list[str], *, include_locations: bool):
    """Recursively expand references in a remote configuration value.

    Parameters
    ----------
    value : object
        Value to expand.
    base_url : str
        Base URL for relative references.
    stack : list[str]
        Active remote include chain.
    include_locations : bool
        Preserve YAML source locations when ``True``.
    """
    if isinstance(value, dict):
        return _expand_remote_dict(value, base_url, stack, include_locations=include_locations)
    if isinstance(value, list):
        return _expand_remote_list(value, base_url, stack, include_locations=include_locations)
    return value


def _expand_remote_dict(
    values: dict[str, Any],
    base_url: str,
    stack: list[str],
    *,
    include_locations: bool,
) -> dict[str, Any]:
    """Expand file and document references within a remote mapping.

    Parameters
    ----------
    values : dict[str, Any]
        Mapping whose values should be expanded in place.
    base_url : str
        Base URL for relative references.
    stack : list[str]
        Active remote include chain.
    include_locations : bool
        Preserve YAML source locations when ``True``.

    Returns
    -------
    dict[str, Any]
        The expanded mapping.
    """
    values.setdefault(REMOTE_BASE_URL_KEY, base_url)
    for key, value in list(values.items()):
        if _is_config_reference(value):
            values[key] = _load_remote_document(
                _resolve_remote_config_reference(value, base_url),
                include_locations=include_locations,
                stack=stack,
            )
            continue

        if isinstance(value, str) and value.startswith(FILE_PREFIX):
            values[key] = resolve_reference(value[len(FILE_PREFIX) :], base_url)
            continue

        values[key] = _expand_remote_value(value, base_url, stack, include_locations=include_locations)
    return values


def _expand_remote_list(values: list[Any], base_url: str, stack: list[str], *, include_locations: bool) -> list[Any]:
    """Expand file and document references within a remote list.

    Parameters
    ----------
    values : list[Any]
        List whose elements should be expanded in place.
    base_url : str
        Base URL for relative references.
    stack : list[str]
        Active remote include chain.
    include_locations : bool
        Preserve YAML source locations when ``True``.

    Returns
    -------
    list[Any]
        The expanded list.
    """
    index = 0
    while index < len(values):
        value = values[index]
        if _is_config_reference(value):
            expanded = _load_remote_document(
                _resolve_remote_config_reference(value, base_url),
                include_locations=include_locations,
                stack=stack,
            )
            if isinstance(expanded, list):
                values[index : index + 1] = expanded
                index += len(expanded)
            else:
                values[index] = expanded
                index += 1
            continue

        if isinstance(value, str) and value.startswith(FILE_PREFIX):
            values[index] = resolve_reference(value[len(FILE_PREFIX) :], base_url)
            index += 1
            continue

        values[index] = _expand_remote_value(value, base_url, stack, include_locations=include_locations)
        index += 1
    return values


def _is_config_reference(value: Any) -> bool:
    """Return whether a value names a supported configuration document.

    Parameters
    ----------
    value : Any
        Value to inspect.

    Returns
    -------
    bool
        ``True`` for a YAML, JSON, or supported remote document reference.
    """
    if not isinstance(value, str):
        return False

    if value.startswith(FILE_PREFIX):
        return False

    parsed = urlparse(value)
    path = parsed.path if parsed.scheme in _REMOTE_SCHEMES else value
    return any(path.endswith(suffix) for suffix in ACCEPTED_SUFFIXES)


def _resolve_remote_config_reference(reference: str, base_url: str) -> str:
    """Resolve a remote include against its containing document URL.

    Parameters
    ----------
    reference : str
        Relative or absolute document reference.
    base_url : str
        Base URL of the containing document.

    Returns
    -------
    str
        Absolute URL of the referenced document.
    """
    if is_remote_url(reference):
        return reference
    return urljoin(base_url, reference)


def _remote_base_url(url: str) -> str:
    """Return the directory-like base URL for a remote document.

    Parameters
    ----------
    url : str
        Remote document URL.

    Returns
    -------
    str
        Base URL used to resolve relative references.
    """
    return urljoin(url, ".")
