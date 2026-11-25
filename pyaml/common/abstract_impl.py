"""Backend-independent implementations of PyAML read/write interfaces."""

from collections.abc import Iterator, Mapping
from types import MappingProxyType


class RInsertionDeviceModelPoint(Mapping[str, float | str]):
    """Read-only reference settings and units, independent of live hardware."""

    def __init__(self, settings: Mapping[str, float | str], units: Mapping[str, str]):
        self._settings = MappingProxyType(dict(settings))
        self._units = MappingProxyType(dict(units))

    def __getitem__(self, name: str) -> float | str:
        return self._settings[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._settings)

    def __len__(self) -> int:
        return len(self._settings)

    @property
    def units(self) -> Mapping[str, str]:
        return self._units

    @property
    def mode(self) -> str | None:
        value = self._settings.get("mode")
        return value if isinstance(value, str) else None
