"""
static_catalog_entry.py

Typed catalog entry used by :mod:`pyaml.configuration.static_catalog`.
"""

from pydantic import BaseModel, ConfigDict

from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS = "StaticCatalogEntry"


class ConfigModel(BaseModel):
    r"""
    Configuration model for :class:`StaticCatalogEntry`.

    Parameters
    ----------
    key : str
        Catalog key resolved by the static catalog.
    device : DeviceAccess
        Device access associated with ``key``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    key: str
    device: DeviceAccess


class StaticCatalogEntry:
    r"""
    Typed entry for :class:`~pyaml.configuration.static_catalog.StaticCatalog`.
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

    def get_key(self) -> str:
        r"""
        Return the catalog key.

        Returns
        -------
        str
            Entry key.
        """
        return self._cfg.key

    def get_device(self) -> DeviceAccess:
        r"""
        Return the device associated with this entry.

        Returns
        -------
        DeviceAccess
            Stored device access.
        """
        return self._cfg.device
