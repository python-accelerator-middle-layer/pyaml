import re
from typing import Pattern

from pyaml import PyAMLException
from pyaml.control.deviceaccessproxy import DeviceAccessProxy

# Stored values in a runtime view: proxies only.
CatalogStored = DeviceAccessProxy | list[DeviceAccessProxy]


class CatalogView:
    """
    Per-ControlSystem runtime view of a ConfigCatalog.

    This view provides stable DeviceAccessProxy handles to consumers.
    When the underlying ConfigCatalog changes, the view refreshes proxies by
    swapping their targets to newly attached devices in the current CS context.

    Core invariants
    ---------------
    - Values exposed by this view are DeviceAccessProxy or list[DeviceAccessProxy].
    - Proxies are stable objects: refresh/update changes targets, not proxy identity.
    - Entry cardinality is shape-stable: prototypes are expected to keep the same
      single vs multi shape once the view is created.
    """

    def __init__(self, config_catalog: "Catalog", control_system: "ControlSystem"):  # noqa: F821
        self._config_catalog = config_catalog
        self._cs = control_system
        self._entries: dict[str, CatalogStored] = {}

    # ------------------------------------------------------------------

    def get_name(self) -> str:
        """Return a helpful display name for this view."""
        return f"{self._config_catalog.get_name()}@{self._cs.name()}"

    # ------------------------------------------------------------------

    def keys(self) -> list[str]:
        """Return all reference keys known by this view."""
        return list(self._entries.keys())

    # ------------------------------------------------------------------

    def has_reference(self, reference: str) -> bool:
        """Return True if the reference exists in this view."""
        return reference in self._entries

    # ------------------------------------------------------------------

    def get(self, reference: str) -> CatalogStored:
        """
        Return a stored value (proxy or list of proxies).

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

    def get_one(self, reference: str) -> DeviceAccessProxy:
        """
        Return a single proxy for this reference.

        Raises
        ------
        PyAMLException
            If the entry is multi-device.
        """
        value = self.get(reference)
        if isinstance(value, list):
            raise PyAMLException(
                f"Catalog reference '{reference}' is multi-device; use get_many()."
            )
        return value

    # ------------------------------------------------------------------

    def get_many(self, reference: str) -> list[DeviceAccessProxy]:
        """
        Return a list of proxies for this reference.

        Raises
        ------
        PyAMLException
            If the entry is single-device.
        """
        value = self.get(reference)
        if not isinstance(value, list):
            raise PyAMLException(
                f"Catalog reference '{reference}' is single-device; use get_one()."
            )
        return value

    # ------------------------------------------------------------------

    def find(self, pattern: str) -> dict[str, CatalogStored]:
        """
        Return entries whose keys match the provided regex.

        Parameters
        ----------
        pattern : str
            Regex pattern applied to keys.

        Returns
        -------
        dict
            Mapping of matching keys to proxies (or list of proxies).
        """
        regex: Pattern[str] = re.compile(pattern)
        return {k: v for k, v in self._entries.items() if regex.search(k)}

    # ------------------------------------------------------------------

    def find_by_prefix(self, prefix: str) -> dict[str, CatalogStored]:
        """
        Return entries whose keys start with the provided prefix.

        Notes
        -----
        - Prefix is matched literally (escaped internally).
        """
        return self.find(rf"^{re.escape(prefix)}")

    # ------------------------------------------------------------------

    def get_sub_catalog(self, pattern: str) -> "CatalogView":
        """
        Create a sub-view containing only entries matching the regex pattern.

        Important
        ---------
        This MUST NOT duplicate proxies. It reuses the same proxy objects,
        so refreshing/updating the parent view is visible through the sub-view.

        Returns
        -------
        CatalogView
            New CatalogView bound to the same ControlSystem and same ConfigCatalog,
            containing only a subset of entries.
        """
        data = self.find(pattern)
        sub = CatalogView(self._config_catalog, self._cs)
        sub._entries.update(data)  # reuse proxies; do not recreate
        return sub

    # ------------------------------------------------------------------

    def get_sub_catalog_by_prefix(self, prefix: str) -> "CatalogView":
        """
        Create a sub-view containing entries whose keys start with 'prefix',
        and strip the prefix from keys in the returned view.

        Important
        ---------
        Proxies are reused and NOT duplicated.

        Raises
        ------
        PyAMLException
            If stripping the prefix yields an empty key.
        """
        sub = CatalogView(self._config_catalog, self._cs)

        for k, v in self._entries.items():
            if k.startswith(prefix):
                nk = k[len(prefix) :]
                if not nk:
                    raise PyAMLException(
                        f"Removing prefix '{prefix}' from '{k}' results in an empty"
                        f" reference."
                    )
                sub._entries[nk] = v  # reuse proxies

        return sub

    # ------------------------------------------------------------------
    # Refresh logic (eager)
    # ------------------------------------------------------------------

    def refresh_all(self):
        """
        Refresh all references from the config catalog.

        This attaches prototypes in the current ControlSystem context and sets
        proxy targets accordingly.
        """
        for ref in self._config_catalog.keys():
            self.refresh_reference(ref)

    # ------------------------------------------------------------------

    def refresh_reference(self, reference: str):
        """
        Refresh one reference from the config catalog.

        Steps
        -----
        1) Ensure proxy handles exist (create them once).
        2) Attach the prototype(s) in the current ControlSystem context.
        3) Update proxy target(s) to the attached device(s).

        Notes
        -----
        - This is eager propagation from ConfigCatalog updates.
        - Actual backend connections remain lazy inside the attached DeviceAccess.
        """
        proto = self._config_catalog.get_proto(reference)

        # Ensure proxy handles exist once
        if reference not in self._entries:
            if isinstance(proto, list):
                self._entries[reference] = [
                    DeviceAccessProxy(reference=f"{reference}[{i}]", target=None)
                    for i in range(len(proto))
                ]
            else:
                self._entries[reference] = DeviceAccessProxy(
                    reference=reference, target=None
                )

        proxies = self._entries[reference]

        # Shape stability: single/multi must not change after creation
        if isinstance(proto, list):
            if not isinstance(proxies, list) or len(proxies) != len(proto):
                raise PyAMLException(
                    f"Catalog view '{self.get_name()}' expects {len(proto)} proxy(ies) "
                    f"for '{reference}' (shape change is not supported)."
                )

            attached = self._cs.attach(proto)  # returns list[DeviceAccess]
            for p, a in zip(proxies, attached, strict=True):
                p.set_target(a)

        else:
            if isinstance(proxies, list):
                raise PyAMLException(
                    f"Catalog view '{self.get_name()}' has multi proxies for"
                    f" '{reference}', but the config prototype is single (shape change "
                    f"is not supported)."
                )

            attached = self._cs.attach([proto])[0]
            proxies.set_target(attached)
