"""Quadrupole magnet elements.

This module defines normal quadrupole configuration and runtime interfaces.
"""

from ..lattice.polynom_info import PolynomInfo
from ..validation import DynamicValidation, register_schema
from .magnet import Magnet
from .model import MagnetModel

# Define the main class name for this module
PYAMLCLASS = "Quadrupole"


@register_schema
class Quadrupole(Magnet, DynamicValidation):
    """Quadrupole class"""

    polynom = PolynomInfo("PolynomB", 1)

    def __init__(
        self, name: str, model: MagnetModel | None = None, lattice_names: str | None = None, description: str | None = None
    ):
        """
        Initialize the Quadrupole.

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
