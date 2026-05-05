from ..common import abstract
from ..lattice.polynom_info import PolynomInfo
from .corrector import RWCorrectorAngle
from .magnet import Magnet, MagnetSchema
from .model import MagnetModel


class VCorrectorSchema(MagnetSchema):
    """Configuration model for Vertical Corrector magnet."""

    ...


class VCorrector(Magnet):
    """Vertical Corrector class"""

    polynom = PolynomInfo("PolynomA", 0)

    def __init__(self, name: str, description: str | None = None, lattice_names: str | None = None, model: MagnetModel = None):
        super().__init__(name, description, lattice_names, model)
        self.__angle = RWCorrectorAngle(self)

    @property
    def angle(self) -> abstract.ReadWriteFloatScalar:
        """
        Set the kick angle.
        """
        return self.__angle
