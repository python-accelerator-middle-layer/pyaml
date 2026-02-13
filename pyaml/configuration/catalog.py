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
    name: str
        Name of the configuration to be reference in the control system
    refs : list[CatalogEntryConfigModel]
        List of catalog entries.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
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
        self._cfg = cfg
        self._entries: dict[str, CatalogValue] = {}
        for ref in cfg.refs:
            self.add(ref.get_reference(), ref.get_value())

    # ------------------------------------------------------------------

    def get_name(self) -> str:
        return self._cfg.name

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

    def find_by_prefix(self, prefix: str) -> dict[str, CatalogValue]:
        """
        Return all catalog entries whose reference starts with
        the given prefix.

        Parameters
        ----------
        prefix : str
            Prefix to match at the beginning of reference keys.

        Returns
        -------
        dict[str, CatalogValue]
            Mapping {reference -> DeviceAccess or list[DeviceAccess]}.

        Notes
        -----
        - The prefix is escaped using re.escape() to avoid
          unintended regular expression behavior.
        - This is a convenience wrapper around `find()`.
        """
        return self.find(rf"^{re.escape(prefix)}")

    # ------------------------------------------------------------------

    def find(self, pattern: str) -> dict[str, CatalogValue]:
        """
        Resolve references matching a regular expression.

        Parameters
        ----------
        pattern : str
            Regular expression applied to reference keys.

        Returns
        -------
        dict[str, DeviceAccess | list[DeviceAccess]]
            Mapping {reference -> value}.
        """
        regex: Pattern[str] = re.compile(pattern)
        return {k: v for k, v in self._entries.items() if regex.search(k)}

    # ------------------------------------------------------------------

    def get_sub_catalog_by_prefix(self, prefix: str) -> "Catalog":
        """
        Create a new Catalog containing only the references
        that start with the given prefix, and remove the prefix
        from the keys in the returned catalog.

        Parameters
        ----------
        prefix : str
            Prefix to match at the beginning of reference keys.

        Returns
        -------
        Catalog
            A new Catalog instance containing only the matching
            references, with the prefix removed from their keys.

        Notes
        -----
        - The prefix is matched literally (no regex behavior).
        - The underlying DeviceAccess instances are NOT copied;
          the same objects are reused.
        - If no references match, an empty Catalog is returned.
        - If removing the prefix results in duplicate keys,
          a PyAMLException is raised.
        """
        sub_catalog = Catalog(ConfigModel(name=self.get_name() + "/" + prefix, refs=[]))

        for key, value in self._entries.items():
            if key.startswith(prefix):
                # Remove prefix from key
                new_key = key[len(prefix) :]

                if not new_key:
                    raise PyAMLException(
                        f"Removing prefix '{prefix}' from '{key}' "
                        "results in an empty reference."
                    )

                sub_catalog.add(new_key, value)

        return sub_catalog

    # ------------------------------------------------------------------

    def get_sub_catalog(self, pattern: str) -> "Catalog":
        """
        Create a new Catalog containing only the references
        matching the given regular expression.

        Parameters
        ----------
        pattern : str
            Regular expression applied to reference keys.

        Returns
        -------
        Catalog
            A new Catalog instance containing only the matching
            references and their associated DeviceAccess objects.

        Notes
        -----
        - The returned catalog is independent from the original one.
        - The underlying DeviceAccess objects are not copied; the
          same instances are reused.
        - If no references match, an empty Catalog is returned.
        """
        data = self.find(pattern)

        # Create a new empty catalog with a derived name
        sub_catalog = Catalog(
            ConfigModel(name=self.get_name() + "/" + pattern, refs=[])
        )

        # Re-register matching entries in the new catalog
        for k, v in data.items():
            sub_catalog.add(k, v)
        return sub_catalog

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
