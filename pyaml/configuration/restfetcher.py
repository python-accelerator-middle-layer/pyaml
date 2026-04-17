"""
HTTP configuration fetch helpers.
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
from .fileloader import FILE_PREFIX, SafeLineLoader, accepted_suffixes

REMOTE_BASE_URL_KEY = "__baseurl__"
SourceRoot = Path | str | None
_REMOTE_SCHEMES = {"http", "https"}


class _NamedStringIO(io.StringIO):
    def __init__(self, value: str, name: str):
        super().__init__(value)
        self.name = name


def is_remote_url(value: str) -> bool:
    return urlparse(value).scheme in _REMOTE_SCHEMES


def fetch_remote_config(url: str, *, use_fast_loader: bool = False) -> tuple[dict[str, Any] | list[Any], str]:
    normalized_url = _normalize_remote_url(url)
    expanded = _load_remote_document(normalized_url, use_fast_loader=use_fast_loader, stack=[])
    return expanded, _remote_base_url(normalized_url)


def resolve_reference(reference: str, source_root: SourceRoot) -> str:
    if is_remote_url(reference) or os.path.isabs(reference):
        return reference

    if isinstance(source_root, Path):
        return str((source_root / reference).resolve())

    if isinstance(source_root, str):
        return urljoin(source_root, reference)

    return reference


def _normalize_remote_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in _REMOTE_SCHEMES:
        raise PyAMLConfigException(f"Unsupported remote configuration source '{url}'.")
    return url


def _load_remote_document(
    url: str,
    *,
    use_fast_loader: bool,
    stack: list[str],
) -> dict[str, Any] | list[Any]:
    if url in stack:
        raise PyAMLConfigException(f"Circular remote configuration inclusion detected for '{url}'.")

    payload, content_type = _download_text(url)
    document = _parse_remote_document(url, payload, content_type, use_fast_loader=use_fast_loader)
    return _expand_remote_value(document, _remote_base_url(url), stack + [url], use_fast_loader=use_fast_loader)


def _download_text(url: str) -> tuple[str, str]:
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
    use_fast_loader: bool,
) -> dict[str, Any] | list[Any]:
    suffix = Path(urlparse(url).path).suffix.lower()

    if content_type == "application/json" or suffix == ".json":
        try:
            return json.loads(payload)
        except json.JSONDecodeError as ex:
            raise PyAMLConfigException(f"{url}: {ex}") from ex

    loader = CLoader if use_fast_loader else SafeLineLoader
    try:
        stream = _NamedStringIO(payload, url)
        return yaml.load(stream, Loader=loader)
    except yaml.YAMLError as ex:
        raise PyAMLConfigException(f"{url}: {ex}") from ex


def _expand_remote_value(value, base_url: str, stack: list[str], *, use_fast_loader: bool):
    if isinstance(value, dict):
        return _expand_remote_dict(value, base_url, stack, use_fast_loader=use_fast_loader)
    if isinstance(value, list):
        return _expand_remote_list(value, base_url, stack, use_fast_loader=use_fast_loader)
    return value


def _expand_remote_dict(
    values: dict[str, Any],
    base_url: str,
    stack: list[str],
    *,
    use_fast_loader: bool,
) -> dict[str, Any]:
    values.setdefault(REMOTE_BASE_URL_KEY, base_url)
    for key, value in list(values.items()):
        if _is_config_reference(value):
            values[key] = _load_remote_document(
                _resolve_remote_config_reference(value, base_url),
                use_fast_loader=use_fast_loader,
                stack=stack,
            )
            continue

        if isinstance(value, str) and value.startswith(FILE_PREFIX):
            values[key] = resolve_reference(value[len(FILE_PREFIX) :], base_url)
            continue

        values[key] = _expand_remote_value(value, base_url, stack, use_fast_loader=use_fast_loader)
    return values


def _expand_remote_list(values: list[Any], base_url: str, stack: list[str], *, use_fast_loader: bool) -> list[Any]:
    index = 0
    while index < len(values):
        value = values[index]
        if _is_config_reference(value):
            expanded = _load_remote_document(
                _resolve_remote_config_reference(value, base_url),
                use_fast_loader=use_fast_loader,
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

        values[index] = _expand_remote_value(value, base_url, stack, use_fast_loader=use_fast_loader)
        index += 1
    return values


def _is_config_reference(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    if value.startswith(FILE_PREFIX):
        return False

    parsed = urlparse(value)
    path = parsed.path if parsed.scheme in _REMOTE_SCHEMES else value
    return any(path.endswith(suffix) for suffix in accepted_suffixes)


def _resolve_remote_config_reference(reference: str, base_url: str) -> str:
    if is_remote_url(reference):
        return reference
    return urljoin(base_url, reference)


def _remote_base_url(url: str) -> str:
    return urljoin(url, ".")
