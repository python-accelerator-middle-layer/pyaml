from pydantic import ConfigDict, model_validator

from pyaml import PyAMLException
from pyaml.configuration.catalog import Catalog, CatalogConfigModel
from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS = "StaticCatalog"


class ConfigModel(CatalogConfigModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    refs: dict[str, DeviceAccess]

    @model_validator(mode="after")
    def validate_refs(self) -> "ConfigModel":
        if len(self.refs) == 0:
            raise ValueError("StaticCatalog.refs must contain at least one entry")
        return self


class StaticCatalog(Catalog):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)
        self._refs = cfg.refs

    def resolve(self, key: str) -> DeviceAccess:
        try:
            return self._refs[key]
        except KeyError as exc:
            raise PyAMLException(f"Catalog '{self.get_name()}' cannot resolve key '{key}'") from exc
