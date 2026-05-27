from ..lattice.polynom_info import PolynomInfo
from ..validation import register_schema
from .magnet import Magnet, MagnetSchema
from .model import MagnetModel


@register_schema(MagnetSchema)
class Sextupole(Magnet):
    """Sextupole class"""

    polynom = PolynomInfo("PolynomB", 2)

    def __init__(self, name: str, description: str | None = None, lattice_names: str | None = None, model: MagnetModel = None):
        super().__init__(name, description, lattice_names, model)
