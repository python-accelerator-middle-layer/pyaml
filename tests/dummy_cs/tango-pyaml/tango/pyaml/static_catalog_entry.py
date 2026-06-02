from pydantic import BaseModel, ConfigDict

from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS = "StaticCatalogEntry"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    key: str
    device: DeviceAccess


class StaticCatalogEntry:
    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

    def get_key(self) -> str:
        return self._cfg.key

    def get_device(self) -> DeviceAccess:
        return self._cfg.device
