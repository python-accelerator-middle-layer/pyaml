import re
from typing import Pattern

from pydantic import BaseModel, ConfigDict, model_validator

from pyaml import PyAMLException
from pyaml.configuration.catalog_entry import CatalogEntry, CatalogValue
from pyaml.configuration.catalog_entry import ConfigModel as CatalogEntryConfigModel
from pyaml.control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "Catalog"


class ConfigModel(BaseModel):
    """
    Configuration model for a value catalog.

    Attributes
    ----------
    refs : list[CatalogEntryConfigModel]
        List of catalog entries.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    refs: list[CatalogEntry]

    @model_validator(mode="after")
    def _validate_unique_references(self) -> "ConfigModel":
        """
        Ensure that all references are unique within the catalog.
        """
        seen: set[str] = set()
        for entry in self.refs:
            if entry.get_reference() in seen:
                raise ValueError(
                    f"Duplicate catalog reference: '{entry.get_reference()}'."
                )
            seen.add(entry.get_reference())
        return self


class Catalog:
    """
    A simple registry mapping reference keys to DeviceAccess objects.

    The catalog is intentionally minimal:
    - It resolves references to DeviceAccess or list[DeviceAccess]
    - It does NOT expose any DeviceAccess-like interface (no get/set/readback/etc.)
    """

    def __init__(self, cfg: ConfigModel):
        self._entries: dict[str, CatalogValue] = {}
        for ref in cfg.refs:
            self.add(ref.get_reference(), ref.get_value())

    # ------------------------------------------------------------------

    def add(self, reference: str, value: CatalogValue):
        """
        Register a reference in the catalog.

        Raises
        ------
        PyAMLException
            If the reference already exists.
        """
        if reference in self._entries:
            raise PyAMLException(f"Duplicate catalog reference: '{reference}'")
        self._entries[reference] = value

    # ------------------------------------------------------------------

    def get(self, reference: str) -> CatalogValue:
        """
        Resolve a reference key.

        Returns
        -------
        DeviceAccess | list[DeviceAccess]

        Raises
        ------
        PyAMLException
            If the reference does not exist.
        """
        try:
            return self._entries[reference]
        except KeyError as exc:
            raise PyAMLException(f"Catalog reference '{reference}' not found.") from exc

    # ------------------------------------------------------------------

    def get_one(self, reference: str) -> DeviceAccess:
        """
        Resolve a reference and ensure it corresponds to a single DeviceAccess.

        Raises
        ------
        PyAMLException
            If the reference does not exist or is multi-device.
        """
        value = self.get(reference)

        if isinstance(value, list):
            raise PyAMLException(
                f"Catalog reference '{reference}' is multi-device; use get_many()."
            )

        return value

    # ------------------------------------------------------------------

    def get_many(self, reference: str) -> list[DeviceAccess]:
        """
        Resolve a reference and ensure it corresponds to multiple DeviceAccess.

        Returns
        -------
        list[DeviceAccess]

        Raises
        ------
        PyAMLException
            If the reference does not exist or is single-device.
        """
        value = self.get(reference)

        if not isinstance(value, list):
            raise PyAMLException(
                f"Catalog reference '{reference}' is single-device; use get_one()."
            )

        return value

    # ------------------------------------------------------------------

    def find(self, pattern: str) -> dict[str, CatalogValue]:
        """
        Resolve references matching a regular expression.

        Returns
        -------
        dict[str, DeviceAccess | list[DeviceAccess]]
            Mapping {reference -> value}.
        """
        regex: Pattern[str] = re.compile(pattern)
        return {k: v for k, v in self._entries.items() if regex.search(k)}

    # ------------------------------------------------------------------

    def keys(self) -> list[str]:
        """Return all catalog reference keys."""
        return list(self._entries.keys())

    # ------------------------------------------------------------------

    def has_reference(self, reference: str) -> bool:
        """
        Return True if the reference exists in the catalog.

        Parameters
        ----------
        reference : str
            Catalog reference key.

        Returns
        -------
        bool
            True if the reference exists, False otherwise.
        """
        return reference in self._entries
