from ..lattice.polynom_info import PolynomInfo
from ..validation import DynamicValidation, register_schema
from .magnet import Magnet
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "SkewSext"


@register_schema
class SkewSext(Magnet, DynamicValidation):
    """SkewSext class"""

    polynom = PolynomInfo("PolynomA", 2)

    def __init__(
        self, name: str, model: MagnetModel | None = None, lattice_names: str | None = None, description: str | None = None
    ):
        super().__init__(name, model, lattice_names, description)
