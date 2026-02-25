from pydantic import BaseModel, ConfigDict, model_validator

from pyaml import PyAMLException
from pyaml.configuration.catalog_entry import CatalogEntry, CatalogTarget
from pyaml.control.catalog_view import CatalogView
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
    Shared configuration catalog.

    This catalog stores *prototypes* (not attached) and can be shared across
    multiple ControlSystem instances.

    Key points
    ----------
    - sr.get_catalog(name) returns this configuration object (as you described).
    - Each ControlSystem (identified by name) uses a per-CS runtime view:
        cfg_catalog.view(control_system)
    - Updates are propagated to all existing views eagerly (refresh occurs
      immediately), while actual device connections remain lazy inside
      DeviceAccess backends.

    Update semantics
    ---------------
    update_proto(reference, proto) updates the shared prototype and triggers a
    refresh of that reference in every existing CatalogView.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        self._protos: dict[str, CatalogTarget] = {}

        # Views indexed by ControlSystem name (instance identity rule).
        self._views: dict[str, CatalogView] = {}

        for ref in cfg.refs:
            self.add_proto(ref.get_reference(), ref.get_value())

    # ------------------------------------------------------------------

    def get_name(self) -> str:
        """Return the catalog name."""
        return self._cfg.name

    # ------------------------------------------------------------------

    def keys(self) -> list[str]:
        """Return all reference keys in this catalog."""
        return list(self._protos.keys())

    # ------------------------------------------------------------------

    def has_reference(self, reference: str) -> bool:
        """Return True if a prototype exists for this reference."""
        return reference in self._protos

    # ------------------------------------------------------------------

    def add_proto(self, reference: str, proto: CatalogTarget):
        """
        Add a new prototype entry.

        Parameters
        ----------
        reference : str
            Reference key.
        proto : DeviceAccess | list[DeviceAccess]
            Prototype device(s), not attached.

        Raises
        ------
        PyAMLException
            If the reference already exists.
        """
        if reference in self._protos:
            raise PyAMLException(f"Duplicate catalog reference: '{reference}'")
        self._protos[reference] = proto
        self._notify_update(reference)

    # ------------------------------------------------------------------

    def update_proto(self, reference: str, proto: CatalogTarget):
        """
        Update an existing prototype entry.

        Parameters
        ----------
        reference : str
            Existing reference key.
        proto : DeviceAccess | list[DeviceAccess]
            New prototype device(s), not attached.

        Raises
        ------
        PyAMLException
            If the reference does not exist.
        """
        if reference not in self._protos:
            raise PyAMLException(f"Catalog reference '{reference}' not found.")
        self._protos[reference] = proto
        self._notify_update(reference)

    # ------------------------------------------------------------------

    def get_proto(self, reference: str) -> CatalogTarget:
        """
        Return the prototype for a given reference.

        Raises
        ------
        PyAMLException
            If the reference does not exist.
        """
        try:
            return self._protos[reference]
        except KeyError as exc:
            raise PyAMLException(f"Catalog reference '{reference}' not found.") from exc

    # ------------------------------------------------------------------

    def view(self, control_system: "ControlSystem") -> CatalogView:  # noqa: F821
        """
        Return a per-ControlSystem runtime view of this catalog.

        Parameters
        ----------
        control_system : ControlSystem
            ControlSystem instance. Its name identifies the view.

        Returns
        -------
        CatalogView
            Runtime view bound to the provided ControlSystem.

        Notes
        -----
        - A view is created once per ControlSystem name and cached.
        - The view is immediately refreshed (all entries attached in that CS context).
        """
        cs_name = control_system.name()
        view = self._views.get(cs_name)
        if view is None:
            view = CatalogView(config_catalog=self, control_system=control_system)
            self._views[cs_name] = view
            view.refresh_all()
        return view

    # ------------------------------------------------------------------

    def _notify_update(self, reference: str):
        """
        Notify all existing views that a reference prototype has changed.

        We choose eager propagation: every view refreshes that reference immediately.
        DeviceAccess backends remain lazy, so this is typically cheap.
        """
        for view in self._views.values():
            view.refresh_reference(reference)
