"""Configuration helpers for backend-provided catalogs."""

from pydantic import BaseModel, ConfigDict


class CatalogConfigModel(BaseModel):
    r"""
    Base configuration model for named catalogs.

    Parameters
    ----------
    name : str
        Unique catalog identifier used in accelerator and control-system
        configuration.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str


class Catalog:
    r"""
    Minimal base for backend catalog configuration objects.

    PyAML keeps catalog configuration objects so they can be attached to
    backend control-system configuration. PyAML itself does not resolve
    catalog keys.

    Notes
    -----
    Concrete catalogs live in each control-system package. They may expose
    backend-specific resolution APIs, but those APIs are not called by the
    PyAML core.
    """

    def __init__(self, cfg: CatalogConfigModel):
        self._cfg = cfg

    def get_name(self) -> str:
        r"""
        Return the catalog name.

        Returns
        -------
        str
            Catalog identifier.
        """
        return self._cfg.name
