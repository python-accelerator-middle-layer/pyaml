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
    """Horizontal Corrector class"""

    polynom = PolynomInfo("PolynomB", 0, HORIZONTAL_KICK_SIGN)

    def __init__(
        self, name: str, model: MagnetModel | None = None, lattice_names: str | None = None, description: str | None = None
    ):
        super().__init__(name, model, lattice_names, description)
        self.__angle = RWCorrectorAngle(self)

    @property
    def angle(self) -> abstract.ReadWriteFloatScalar:
        """
        Set the kick angle.
        """
        return self.__angle

    def attach(
        self,
        peer,
        strength: abstract.ReadWriteFloatScalar,
        hardware: abstract.ReadWriteFloatScalar,
    ) -> Self:
        """
        Create a new reference to attach this magnet to a simulator
        or a control systemand.
        """
        obj = super().attach(peer, strength, hardware)
        obj.__angle = RWCorrectorAngle(obj)
        return obj
