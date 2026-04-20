"""
static_catalog.py

Built-in mapping-based catalog implementation for PyAML.
"""

from pydantic import ConfigDict

from pyaml import PyAMLException
from pyaml.configuration.catalog import Catalog, CatalogConfigModel
from pyaml.configuration.static_catalog_entry import StaticCatalogEntry
from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS = "StaticCatalog"


class ConfigModel(CatalogConfigModel):
    r"""
    Configuration model for :class:`StaticCatalog`.

    Parameters
    ----------
    name : str
        Catalog identifier.
    entries : list[StaticCatalogEntry]
        Explicit list of typed entries mapping catalog keys to device access objects.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    entries: list[StaticCatalogEntry]


class StaticCatalog(Catalog):
    r"""
    Catalog implementation backed by explicit typed entries.

    :class:`StaticCatalog` is the standard catalog implementation
    provided by base PyAML. It resolves configuration keys directly
    from the mapping declared in the configuration file.

    Examples
    --------

    .. code-block:: yaml

        catalogs:
          - type: pyaml.configuration.static_catalog
            name: bpm-common
            entries:
              - type: pyaml.configuration.static_catalog_entry
                key: BPM_C01-01/x
                device:
                  type: tango.pyaml.attribute_read_only
                  attribute: srdiag/bpm/c01-01/XPosSA
                  unit: mm
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)
        if len(cfg.entries) == 0:
            raise PyAMLException("StaticCatalog.entries must contain at least one entry")

        self._refs: dict[str, DeviceAccess] = {}
        for entry in cfg.entries:
            key = entry.get_key()
            if key in self._refs:
                raise PyAMLException(f"StaticCatalog.entries contains duplicate key '{key}'")
            self._refs[key] = entry.get_device()

    def resolve(self, key: str) -> DeviceAccess:
        r"""
        Resolve a key from the static mapping.

        Parameters
        ----------
        key : str
            Catalog key to resolve.

        Returns
        -------
        DeviceAccess
            Device access stored for ``key``.

        Raises
        ------
        PyAMLException
            If the key is not present in the catalog.
        """
        try:
            return self._refs[key]
        except KeyError as exc:
            raise PyAMLException(f"Catalog '{self.get_name()}' cannot resolve key '{key}'") from exc
