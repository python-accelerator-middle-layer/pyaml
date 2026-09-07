import numpy as np

from pyaml.validation import DynamicValidation, register_schema

from .. import PyAMLException
from ..common.element import __pyaml_repr__
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "IdentityMagnetModel"


@register_schema
class IdentityMagnetModel(MagnetModel, DynamicValidation):
    """
    Identity magnet model.

    This model maps magnet strengths directly to hardware values without applying
    any conversion. It is intended for cases where the physics value and the
    hardware value are identical, so the model behaves as an identity transform.

    Parameters
    ----------
    powerconverter : str | None, optional
        Name of the power converter device used to apply current.
    physics : str | None, optional
        Name of the physics device used to apply strength.
    unit : str | None, optional
        Unit of the magnet strength and hardware value, for example ``"1/m"`` or
        ``"m-1"``.

    Raises
    ------
    PyAMLException
        If both ``physics`` and ``powerconverter`` are missing, or if both are
        provided at the same time.

    Notes
    -----
    The model does not perform any numerical conversion: strengths are returned
    as hardware values and hardware values are returned as strengths.
    """

    def __init__(
        self,
        powerconverter: str | None = None,
        physics: str | None = None,
        unit: str | None = None,
    ):
        self._physics = physics
        self._powerconverter = powerconverter
        self._unit = unit

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
        return [self._unit]

    def get_hardware_units(self) -> list[str]:
        return [self._unit]

    def get_device_names(self) -> list[str | None]:
        return [self.__device]

    def set_magnet_rigidity(self, brho: np.double):
        pass

    def has_physics(self) -> bool:
        return self._physics is not None

    def has_hardware(self) -> bool:
        return self._powerconverter is not None

    def __repr__(self):
        return __pyaml_repr__(self)
