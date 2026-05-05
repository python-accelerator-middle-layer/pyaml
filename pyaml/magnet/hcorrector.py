from ..common import abstract
from ..common.constants import HORIZONTAL_KICK_SIGN
from ..lattice.polynom_info import PolynomInfo
from .corrector import RWCorrectorAngle
from .magnet import Magnet, MagnetSchema
from .model import MagnetModel


class HCorrectorSchema(MagnetSchema):
    """Configuration model for Horizontal Corrector magnet."""

    ...


class HCorrector(Magnet):
    """Horizontal Corrector class"""

    polynom = PolynomInfo("PolynomB", 0, HORIZONTAL_KICK_SIGN)

    def __init__(
        self, name: str, description: str | None = None, lattice_names: str | None = None, model: MagnetModel = None
    ):
        super().__init__(name, description, lattice_names, model)
        self.__angle = RWCorrectorAngle(self)

    @property
    def angle(self) -> abstract.ReadWriteFloatScalar:
        """
        Set the kick angle.
        """
        return self.__angle
