from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from pyaml.control.deviceaccess import DeviceAccess

if TYPE_CHECKING:
    from pyaml.control.controlsystem import ControlSystem


class CatalogConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str


class Catalog(metaclass=ABCMeta):
    """Base abstraction for resolving a key into a DeviceAccess."""

    def __init__(self, cfg: CatalogConfigModel):
        self._cfg = cfg

    def get_name(self) -> str:
        return self._cfg.name

    def attach_control_system(self, control_system: "ControlSystem"):
        """Lifecycle hook called when a control system attaches this catalog."""
        return None

    @abstractmethod
    def resolve(self, key: str) -> DeviceAccess:
        """Resolve a catalog key into a concrete DeviceAccess."""
        raise NotImplementedError
