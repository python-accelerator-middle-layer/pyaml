from ..lattice.polynom_info import PolynomInfo
from .magnet import Magnet, MagnetSchema
from .model import MagnetModel


class QuadrupoleSchema(MagnetSchema):
    """Schema for Quadrupole magnet."""

    ...


class Quadrupole(Magnet):
    """Quadrupole class"""

    polynom = PolynomInfo("PolynomB", 1)

    def __init__(
        self, name: str, description: str | None = None, lattice_names: str | None = None, model: MagnetModel = None
    ):
        super().__init__(name, description, lattice_names, model)
