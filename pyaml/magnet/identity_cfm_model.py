import numpy as np
from pydantic import BaseModel, ConfigDict

from .. import PyAMLException
from ..common.element import __pyaml_repr__
from ..configuration import ConfigurationSchema, register_schema
from ..control.deviceaccess import DeviceAccess, DeviceAccessSchema
from .model import MagnetModel


class IdentityCFMagnetModelSchema(ConfigurationSchema):
    """
    Configuration model for identity combined function magnet model

    Parameters
    ----------
    multipoles : list[str]
        List of supported functions: A0, B0, A1, B1, etc (i.e. [B0, A1, B2])
    powerconverters : list[DeviceAccess], optional
        Power converter devices to apply current
    physics : list[DeviceAccess], optional
        Magnet devices to apply strength
    units : list[str]
        List of strength units (i.e. ['rad', 'm-1', 'm-2'])
    """

    model_config = ConfigDict(extra="forbid")

    multipoles: list[str]
    powerconverters: list[DeviceAccessSchema | None] | None = None
    physics: list[DeviceAccessSchema | None] | None = None
    units: list[str] = ""


@register_schema(IdentityCFMagnetModelSchema)
class IdentityCFMagnetModel(MagnetModel):
    """
    Class that map values to underlying devices without conversion
    """

    def __init__(
        self,
        multipoles: list[str],
        powerconverters: list[DeviceAccess | None] | None = None,
        physics: list[DeviceAccess | None] | None = None,
        units: list[str] = "",
    ):
        self._multipoles = multipoles
        self._powerconverters = powerconverters
        self._physics = physics
        self._units = units

        # Check config
        self.__nbFunction: int = len(self._multipoles)

        if self._physics is None and self._powerconverters is None:
            raise PyAMLException("Invalid IdentityCFMagnetModel configuration,physics or powerconverters device required")
        if self._physics is not None and self._powerconverters is not None:
            raise PyAMLException(
                "Invalid IdentityCFMagnetModel configuration,physics or powerconverters device required but not both"
            )
        if self._physics:
            self.__devices = self._physics
        else:
            self.__devices = self._powerconverters

        self.__nbDev: int = len(self.__devices)

        self.__check_len(self._units, "units", self.__nbFunction)

    def __check_len(self, obj, name, expected_len):
        lgth = len(obj)
        if lgth != expected_len:
            raise PyAMLException(
                f"{name} does not have the expected number of items ({expected_len} items expected but got {lgth})"
            )

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        return strengths

    def compute_strengths(self, currents: np.array) -> np.array:
        return currents

    def get_strength_units(self) -> list[str]:
        return self._units

    def get_hardware_units(self) -> list[str]:
        return self._units

    def get_devices(self) -> list[DeviceAccess | None]:
        return self.__devices

    def set_magnet_rigidity(self, brho: np.double):
        pass

    def has_physics(self) -> bool:
        return self._physics is not None

    def has_hardware(self) -> bool:
        return self._powerconverters is not None

    def __repr__(self):
        return __pyaml_repr__(self)
