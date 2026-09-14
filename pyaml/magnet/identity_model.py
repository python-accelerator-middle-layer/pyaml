"""
Identity conversion model for magnets without calibration curves.

This model passes physical values through to hardware values, subject to the configured units and magnetic-rigidity scaling.
"""

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

    Methods
    -------
    compute_hardware_values(strengths)
        Convert magnet strengths to hardware values.
    compute_strengths(currents)
        Convert hardware values to magnet strengths.
    get_strength_units()
        Return the units of magnet strengths.
    get_hardware_units()
        Return the units of hardware values.
    get_device_names()
        Return the associated device names.
    set_magnet_rigidity(brho)
        Set the magnetic rigidity used for conversion.
    has_physics()
        Return whether the model provides physics strengths.
    has_hardware()
        Return whether the model provides hardware values.

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
        """
        Initialize the IdentityMagnetModel.
        """
        self.physics = physics
        self.powerconverter = powerconverter
        self.unit = unit

        if self.physics is None and self.powerconverter is None:
            raise PyAMLException("Invalid IdentityMagnetModel configuration,physics or powerconverter device required")
        if self.physics is not None and self.powerconverter is not None:
            raise PyAMLException(
                "Invalid IdentityMagnetModel configuration,physics or powerconverter device required but not both"
            )
        if self.physics:
            self.__device = self.physics
        else:
            self.__device = self.powerconverter

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        """
        Convert magnet strengths to hardware values.

        Parameters
        ----------
        strengths : np.array
            Magnet strengths to convert, in the unit reported by :meth:`get_strength_unit`.

        Returns
        -------
        np.array
            Hardware values corresponding to ``strengths``.
        """
        return strengths

    def compute_strengths(self, currents: np.array) -> np.array:
        """
        Convert hardware values to magnet strengths.

        Parameters
        ----------
        currents : np.array
            Hardware values to convert, in the unit reported by :meth:`get_hardware_unit`.

        Returns
        -------
        np.array
            Strengths corresponding to ``currents``.
        """
        return currents

    def get_strength_units(self) -> list[str]:
        """Return the units of magnet strengths."""
        return [self.unit]

    def get_hardware_units(self) -> list[str]:
        """Return the units of hardware values."""
        return [self.unit]

    def get_device_names(self) -> list[str | None]:
        """Return the associated device names."""
        return [self.__device]

    def set_magnet_rigidity(self, brho: np.double):
        """
        Set the magnetic rigidity used for conversion.

        Parameters
        ----------
        brho : np.double
            Magnetic rigidity in tesla metres. Ignored: an identity model applies no rigidity scaling.
        """
        pass

    def has_physics(self) -> bool:
        """Return whether the model provides physics strengths."""
        return self.physics is not None

    def has_hardware(self) -> bool:
        """Return whether the model provides hardware values."""
        return self.powerconverter is not None

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
