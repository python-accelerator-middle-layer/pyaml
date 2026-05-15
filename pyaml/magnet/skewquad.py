from ..configuration.schema_registry import register_schema
from ..lattice.polynom_info import PolynomInfo
from .magnet import Magnet, MagnetSchema
from .model import MagnetModel


class SkewQuadSchema(MagnetSchema):
    """Configuration model for SkewQuad magnet."""

    ...


@register_schema(SkewQuadSchema)
class SkewQuad(Magnet):
    """SkewQuad class"""

    polynom = PolynomInfo("PolynomA", 1)

    def __init__(
        self, name: str, description: str | None = None, lattice_names: str | None = None, model: MagnetModel = None
    ):
        super().__init__(name, description, lattice_names, model)
