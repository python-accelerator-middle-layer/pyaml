from pydantic import ConfigDict

from pyaml import PyAMLException
from pyaml.configuration.catalog import Catalog, CatalogConfigModel
from pyaml.control.deviceaccess import DeviceAccess

from .static_catalog_entry import StaticCatalogEntry

PYAMLCLASS = "StaticCatalog"


class ConfigModel(CatalogConfigModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    entries: list[StaticCatalogEntry]


class StaticCatalog(Catalog):
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
        try:
            return self._refs[key]
        except KeyError as exc:
            raise PyAMLException(f"Catalog '{self.get_name()}' cannot resolve key '{key}'") from exc
