from typing import Union

from pydantic import BaseModel, ConfigDict, model_validator

from pyaml.control.deviceaccess import DeviceAccess

# Define the main class name for this module
PYAMLCLASS = "CatalogEntry"


class ConfigModel(BaseModel):
    """
    Configuration model for a single catalog entry.

    Exactly one of 'device' or 'devices' must be provided.

    Attributes
    ----------
    reference : str
        Unique key used to identify the value in the catalog.
    device : dict | None
        Factory configuration dict for a single DeviceAccess.
    devices : list[DeviceAccess] | None
        Factory configuration dicts for multiple DeviceAccess objects.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    reference: str
    device: DeviceAccess = None
    devices: list[DeviceAccess] = None

    @model_validator(mode="after")
    def _validate_one_of(self) -> "ConfigModel":
        """
        Ensure exactly one of (device, devices) is provided and properly shaped.
        """
        has_device = self.device is not None
        has_devices = self.devices is not None and len(self.devices) > 0

        # both True or both False -> invalid
        if has_device == has_devices:
            raise ValueError(
                "Catalog entry must define exactly one of 'device' or 'devices'."
            )

        if has_device and not isinstance(self.device, DeviceAccess):
            raise ValueError("'device' must be a DeviceAccess.")

        if has_devices:
            if not isinstance(self.devices, list) or len(self.devices) == 0:
                raise ValueError("'devices' must be a non-empty list.")
            for i, d in enumerate(self.devices):
                if not isinstance(d, DeviceAccess):
                    raise ValueError(f"'devices[{i}]' must be a DeviceAccess.")

        return self


CatalogValue = Union[DeviceAccess, list[DeviceAccess]]


class CatalogEntry:
    def __init__(self, cfg: ConfigModel):
        self._cfg: ConfigModel = cfg
        self._value: CatalogValue = (
            cfg.device if cfg.device is not None else cfg.devices
        )

    def get_reference(self) -> str:
        return self._cfg.reference

    def get_value(self) -> CatalogValue:
        return self._value
