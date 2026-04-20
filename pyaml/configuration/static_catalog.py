"""
static_catalog.py

Built-in mapping-based catalog implementation for PyAML.
"""

from pydantic import ConfigDict, model_validator

from pyaml import PyAMLException
from pyaml.configuration.catalog import Catalog, CatalogConfigModel
from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS = "StaticCatalog"


class ConfigModel(CatalogConfigModel):
    r"""
    Configuration model for :class:`StaticCatalog`.

    Parameters
    ----------
    name : str
        Catalog identifier.
    refs : dict[str, DeviceAccess]
        Explicit mapping from catalog keys to device access objects.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    refs: dict[str, DeviceAccess]

    @model_validator(mode="after")
    def validate_refs(self) -> "ConfigModel":
        r"""
        Validate that the catalog contains at least one mapping entry.

        Returns
        -------
        ConfigModel
            The validated configuration model.
        """
        if len(self.refs) == 0:
            raise ValueError("StaticCatalog.refs must contain at least one entry")
        return self


class StaticCatalog(Catalog):
    r"""
    Catalog implementation backed by an explicit ``key -> DeviceAccess`` mapping.

    :class:`StaticCatalog` is the standard catalog implementation
    provided by base PyAML. It resolves configuration keys directly
    from the mapping declared in the configuration file.

    Examples
    --------

    .. code-block:: yaml

        catalogs:
          - type: pyaml.configuration.static_catalog
            name: bpm-common
            refs:
              BPM_C01-01/x:
                type: tango.pyaml.attribute_read_only
                attribute: srdiag/bpm/c01-01/XPosSA
                unit: mm
    """

    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)
        self._refs = cfg.refs

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
