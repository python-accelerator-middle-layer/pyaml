"""
Vertical orbit-corrector elements.

This module defines the vertical corrector configuration and runtime
interface, including its vertical kick-angle access.
"""

from typing import Self

from ..common import abstract
from ..lattice.polynom_info import PolynomInfo
from ..validation import DynamicValidation, register_schema
from .corrector import RWCorrectorAngle
from .magnet import Magnet
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "VCorrector"


@register_schema
class VCorrector(Magnet, DynamicValidation):
    """
    Represent a vertical orbit corrector.

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

    Attributes
    ----------
    angle
        Return read/write access to the vertical kick angle in radians.

    Methods
    -------
    attach(peer, strength, hardware)
        Return an attached copy with a bound vertical-angle handle.
    """

    polynom = PolynomInfo("PolynomA", 0)

    def __init__(
        self, name: str, model: MagnetModel | None = None, lattice_names: str | None = None, description: str | None = None
    ):
        """
        Initialize the VCorrector.
        """
        super().__init__(name, model, lattice_names, description)
        self.__angle = RWCorrectorAngle(self)

    @property
    def angle(self) -> abstract.ReadWriteFloatScalar:
        """
        Return read/write access to the vertical kick angle in radians.
        """
        return self.__angle

    def attach(
        self,
        peer,
        strength: abstract.ReadWriteFloatScalar,
        hardware: abstract.ReadWriteFloatScalar,
    ) -> Self:
        """
        Return an attached copy with a bound vertical-angle handle.

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
