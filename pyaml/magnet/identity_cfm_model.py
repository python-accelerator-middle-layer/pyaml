"""
Identity conversion model for combined-function magnets.

This model provides direct per-multipole conversion without excitation-curve interpolation.
"""

import numpy as np

from .. import PyAMLException
from ..common.element import __pyaml_repr__
from ..validation import DynamicValidation, register_schema
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "IdentityCFMagnetModel"


@register_schema
class IdentityCFMagnetModel(MagnetModel, DynamicValidation):
    """
    Identity combined-function magnet model.

    This magnet model maps strengths and hardware values directly to the
    underlying devices without applying any conversion. It is intended for cases
    where the physics values and hardware values are identical, so the model acts
    as an identity transform for all supported multipoles.

    Parameters

    multipoles : list[str]
    List of supported multipoles, for example ["B0", "A1", "B2"].
    powerconverters : list[str | None] | None, optional
    Names of the power converter devices used for hardware access.
    physics : list[str | None] | None, optional
    Names of the physics devices used for strength access.
    units : list[str] | None, optional
    List of units for the supported multipoles.

    Raises

    PyAMLException
    If both physics and powerconverters are missing, if both are
    provided at the same time, or if the configuration lengths do not match.
    """

    def __init__(
        self,
        multipoles: list[str],
        powerconverters: list[str | None] | None = None,
        physics: list[str | None] | None = None,
        units: list[str] | None = None,
    ):
        """
        Initialize the IdentityCFMagnetModel.

        Parameters
        ----------
        multipoles : list[str]
            List of supported multipoles, for example ["B0", "A1", "B2"].
        powerconverters : list[str | None] | None
            Names of the power converter devices used for hardware access.
        physics : list[str | None] | None
            Names of the physics devices used for strength access.
        units : list[str] | None
            List of units for the supported multipoles.
        """
        self.multipoles = multipoles
        self._powerconverters = powerconverters
        self._physics = physics
        self.units = units

        # Check config
        self.__nbFunction: int = len(multipoles)

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

        self.__check_len(self.units, "units", self.__nbFunction)

    def __check_len(self, obj, name, expected_len):
        """
        Validate the length of a model configuration sequence.

        Parameters
        ----------
        obj : object
            Sequence whose length should be checked.
        name : object
            Configuration-field name used in an error message.
        expected_len : object
            Required number of entries.

        Raises
        ------
        PyAMLException
            If ``obj`` does not contain ``expected_len`` entries.
        """
        lgth = len(obj)
        if lgth != expected_len:
            raise PyAMLException(
                f"{name} does not have the expected number of items ({expected_len} items expected but got {lgth})"
            )

    def compute_hardware_values(self, strengths: np.array) -> np.array:
        """
        Convert magnet strengths to hardware values.

        Parameters
        ----------
        strengths : np.array
            Strength of each magnet function, ordered as declared by the model.

        Returns
        -------
        np.array
            Hardware value of each power converter, ordered as declared by the model.
        """
        return strengths

    def compute_strengths(self, currents: np.array) -> np.array:
        """
        Convert hardware values to magnet strengths.

        Parameters
        ----------
        currents : np.array
            Hardware value of each power converter, ordered as declared by the model.

        Returns
        -------
        np.array
            Strength of each magnet function, ordered as declared by the model.
        """
        return currents

    def get_strength_units(self) -> list[str]:
        """Return the units of magnet strengths."""
        return self.units

    def get_hardware_units(self) -> list[str]:
        """Return the units of hardware values."""
        return self.units

    def get_device_names(self) -> list[str | None]:
        """Return the associated device names."""
        return self.__devices

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
        return self._physics is not None

    def has_hardware(self) -> bool:
        """Return whether the model provides hardware values."""
        return self._powerconverters is not None

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
