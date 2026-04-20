from pydantic import ConfigDict

from pyaml import PyAMLException
from pyaml.configuration.catalog import Catalog, CatalogConfigModel

from .attribute import Attribute
from .attribute import ConfigModel as AttributeConfigModel
from .attribute_read_only import AttributeReadOnly
from .attribute_read_only import ConfigModel as AttributeReadOnlyConfigModel

PYAMLCLASS = "AttributeCatalog"


class ConfigModel(CatalogConfigModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    read_only: bool = False
    unit: str = ""


class AttributeCatalog(Catalog):
    def __init__(self, cfg: ConfigModel):
        super().__init__(cfg)
        self._attached_control_systems: list[str] = []

    def attach_control_system(self, control_system):
        self._attached_control_systems.append(control_system.name())

    def resolve(self, key: str):
        if not self._attached_control_systems:
            raise PyAMLException(f"Catalog '{self.get_name()}' must be attached to a control system before resolve()")

        if self._cfg.read_only:
            return AttributeReadOnly(AttributeReadOnlyConfigModel(attribute=key, unit=self._cfg.unit))
        return Attribute(AttributeConfigModel(attribute=key, unit=self._cfg.unit))

    def attached_control_systems(self) -> list[str]:
        return self._attached_control_systems
