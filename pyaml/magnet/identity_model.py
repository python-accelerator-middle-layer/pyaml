import numpy as np
from pydantic import BaseModel, ConfigDict

from .. import PyAMLException
from ..common.element import __pyaml_repr__
from ..configuration import ConfigurationSchema, register_schema
from ..control.deviceaccess import DeviceAccess, DeviceAccessSchema
from .model import MagnetModel


class IdentityMagnetModelSchema(ConfigurationSchema):
    """
    Configuration model for identity magnet model

    Parameters
    ----------
    powerconverter : DeviceAccess, optional
        Power converter device to apply current
    physics : DeviceAccess, optional
        Magnet device to apply strength
    unit : str
        Unit of the strength (i.e. 1/m or m-1)
    """

    model_config = ConfigDict(extra="forbid")

    powerconverter: DeviceAccessSchema | None = None
    physics: DeviceAccessSchema | None = None
    unit: str = ""


@register_schema(IdentityMagnetModelSchema)
class IdentityMagnetModel(MagnetModel):
    """
    Class that map value to underlying device without conversion
    """

    def __init__(
        self,
        powerconverter: DeviceAccess | None = None,
        physics: DeviceAccess | None = None,
        unit: str = "",
    ):
        self._powerconverter = powerconverter
        self._physics = physics
        self.__unit = unit

        if self._physics is None and self._powerconverter is None:
            raise PyAMLException("Invalid IdentityMagnetModel configuration,physics or powerconverter device required")
        if self._physics is not None and self._powerconverter is not None:
            raise PyAMLException(
                "Invalid IdentityMagnetModel configuration,physics or powerconverter device required but not both"
            )
        if self._physics:
            self.__device = self._physics
        else:
            self.__device = self._powerconverter

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        return strengths

    def compute_strengths(self, currents: np.array) -> np.array:
        return currents

    def get_strength_units(self) -> list[str]:
        return [self.__unit]

    def get_hardware_units(self) -> list[str]:
        return [self.__unit]

    def get_devices(self) -> list[DeviceAccess]:
        return [self.__device]

    def set_magnet_rigidity(self, brho: np.double):
        pass

    def has_physics(self) -> bool:
        return self._physics is not None

    def has_hardware(self) -> bool:
        return self._powerconverter is not None

    def __repr__(self):
        return __pyaml_repr__(self)
