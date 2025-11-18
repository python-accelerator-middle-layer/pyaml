from dataclasses import dataclass
from abc import ABCMeta, abstractmethod
import json
import hashlib

from pydantic import BaseModel

ControlSysConfig = BaseModel

from .container import Setpoint, Readback


def get_pydantic_model_hash(model: BaseModel) -> str:

    d = model.model_dump(mode="json")
    data_bytes = json.dumps(d, sort_keys=True, indent=None).encode()

    h = hashlib.sha256(data_bytes).hexdigest()[:16]
    return h


@dataclass(frozen=True)
class _ContainerKey:
    cs_name: str
    cfg_hash: str


class SignalContainerPool(metaclass=ABCMeta):
    def __init__(self):
        self._cache: dict[_ContainerKey, tuple[Setpoint | None, Readback | None]] = {}

    def _key(self, cs_name: str, cs_cfg: ControlSysConfig) -> _ContainerKey:
        return _ContainerKey(cs_name, get_pydantic_model_hash(cs_cfg))

    @abstractmethod
    def _create_setpoint_readback(
        self, cs_name: str, cs_cfg: ControlSysConfig
    ) -> tuple[Setpoint | None, Readback | None]:
        """Create a setpoint/readback pair for the given control system name and configuration,
        and save them in the cache with the key."""
        ...

    def get(
        self, cs_name: str, cs_cfg: ControlSysConfig
    ) -> tuple[Setpoint | None, Readback | None]:
        key = self._key(cs_name, cs_cfg)
        if key in self._cache:
            return self._cache[key]

        return self._create_setpoint_readback(cs_name, cs_cfg)
