from ..configuration.schema_registry import register_schema
from ..lattice.polynom_info import PolynomInfo
from .magnet import Magnet, MagnetSchema
from .model import MagnetModel


class OctupoleSchema(MagnetSchema):
    """Configuration model for Sextupole magnet."""

    ...


@register_schema(OctupoleSchema)
class Octupole(Magnet):
    """Octupole class"""

    polynom = PolynomInfo("PolynomB", 3)

    def __init__(
        self, name: str, description: str | None = None, lattice_names: str | None = None, model: MagnetModel = None
    ):
        super().__init__(name, description, lattice_names, model)
