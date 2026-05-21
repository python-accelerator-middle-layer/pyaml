from ..configuration import register_schema
from ..lattice.polynom_info import PolynomInfo
from .magnet import Magnet, MagnetSchema
from .model import MagnetModel


class SkewOctuSchema(MagnetSchema):
    """Configuration model for SkewOctu magnet."""

    ...


@register_schema(SkewOctuSchema)
class SkewOctu(Magnet):
    """SkewOctu class"""

    polynom = PolynomInfo("PolynomA", 3)

    def __init__(self, name: str, description: str | None = None, lattice_names: str | None = None, model: MagnetModel = None):
        super().__init__(name, description, lattice_names, model)
