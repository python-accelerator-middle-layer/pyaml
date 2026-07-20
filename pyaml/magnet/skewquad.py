from ..lattice.polynom_info import PolynomInfo
from ..validation import DynamicValidation, register_schema
from .magnet import Magnet
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "SkewQuad"


@register_schema
class SkewQuad(Magnet, DynamicValidation):
    """SkewQuad class"""

    polynom = PolynomInfo("PolynomA", 1)

    def __init__(
        self, name: str, model: MagnetModel | None = None, lattice_names: str | None = None, description: str | None = None
    ):
        super().__init__(name, model, lattice_names, description)
