"""
Horizontal orbit-corrector elements.

This module defines the horizontal corrector configuration and runtime
interface, including its horizontal kick-angle access.
"""

from typing import Self

from ..common import abstract
from ..common.constants import HORIZONTAL_KICK_SIGN
from ..lattice.polynom_info import PolynomInfo
from ..validation import DynamicValidation, register_schema
from .corrector import RWCorrectorAngle
from .magnet import Magnet
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "HCorrector"


@register_schema
class HCorrector(Magnet, DynamicValidation):
    """Represent a horizontal orbit corrector."""

    polynom = PolynomInfo("PolynomB", 0, HORIZONTAL_KICK_SIGN)

    def __init__(
        self, name: str, model: MagnetModel | None = None, lattice_names: str | None = None, description: str | None = None
    ):
        """
        Initialize the HCorrector.

        Parameters
        ----------
        name : str
            Corrector name.
        model : MagnetModel | None
            Optional magnet model.
        lattice_names : str | None
            Optional lattice-element mapping.
        description : str | None
            Optional human-readable description.
        """
        super().__init__(name, model, lattice_names, description)
        self.__angle = RWCorrectorAngle(self)

    @property
    def angle(self) -> abstract.ReadWriteFloatScalar:
        """
        Return read/write access to the horizontal kick angle in radians.
        """
        return self.__angle

    def attach(
        self,
        peer,
        strength: abstract.ReadWriteFloatScalar,
        hardware: abstract.ReadWriteFloatScalar,
    ) -> Self:
        """
        Return an attached copy with a bound horizontal-angle handle.

        Parameters
        ----------
        peer : ElementHolder
            Control system or simulator the copy is bound to.
        strength : abstract.ReadWriteFloatScalar
            Accessor for the physical strength on that peer.
        hardware : abstract.ReadWriteFloatScalar
            Accessor for the hardware value on that peer.

        Returns
        -------
        Self
            Copy of this magnet bound to ``peer``.
        """
        obj = super().attach(peer, strength, hardware)
        obj.__angle = RWCorrectorAngle(obj)
        return obj
