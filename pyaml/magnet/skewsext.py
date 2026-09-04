"""Skew-sextupole magnet elements.

This module defines skew-sextupole configuration and runtime interfaces.
"""

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
        """
        Initialize the SkewSext.

        Parameters
        ----------
        name : str
            Input value for this operation.
        model : MagnetModel | None
            Input value for this operation.
        lattice_names : str | None
            Input value for this operation.
        description : str | None
            Input value for this operation.
        """
        super().__init__(name, model, lattice_names, description)
