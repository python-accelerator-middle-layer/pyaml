from pydantic import ConfigDict

from pyaml.common.exception import PyAMLException
from pyaml.configuration.catalog import Catalog, CatalogConfigModel, CatalogResolver
from pyaml.control.deviceaccess import DeviceAccess

PYAMLCLASS = "TangoCatalog"


class ConfigModel(CatalogConfigModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    disconnected: bool = False


class TangoCatalog(Catalog):
    def resolve(self, key: str) -> DeviceAccess:
        raise PyAMLException(
            f"Tango catalog '{self.get_name()}' must be attached to a TangoControlSystem before resolving key '{key}'"
        )

    def attach_control_system(self, control_system):
        from .controlsystem import TangoControlSystem

        if not isinstance(control_system, TangoControlSystem):
            raise PyAMLException(f"Tango catalog '{self.get_name()}' can only be attached to TangoControlSystem")
        return TangoCatalogResolver(self, control_system)


class TangoCatalogResolver(CatalogResolver):
    def __init__(self, catalog: TangoCatalog, control_system):
        self._catalog = catalog
        self._control_system = control_system
        self._refs: dict[str, DeviceAccess] = {}

    def resolve(self, key: str) -> DeviceAccess:
        if key not in self._refs:
            attr_path, index = self._parse_key(key)
            from .attribute import Attribute
            from .attribute import ConfigModel as AttributeConfigModel

            self._refs[key] = Attribute(AttributeConfigModel(attribute=attr_path, index=index))
        return self._refs[key]

    def _parse_key(self, key: str) -> tuple[str, int | None]:
        if not isinstance(key, str):
            raise PyAMLException(f"Tango catalog '{self._catalog.get_name()}' expects string keys, got {type(key).__name__}")
        if "@" in key:
            attr_path, idx_str = key.rsplit("@", 1)
            try:
                index = int(idx_str)
            except ValueError:
                raise PyAMLException(
                    f"Tango catalog '{self._catalog.get_name()}' invalid index '{idx_str}' in key '{key}'."
                ) from None
        else:
            attr_path = key
            index = None

        parts = attr_path.split("/")
        if len(parts) != 4 or any(part == "" for part in parts):
            raise PyAMLException(
                f"Tango catalog '{self._catalog.get_name()}' cannot resolve invalid Tango attribute "
                f"reference '{key}'. Expected 'domain/family/member/attribute' or "
                f"'domain/family/member/attribute@index'."
            )
        return attr_path, index
