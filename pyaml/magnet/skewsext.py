"""
Skew-sextupole magnet elements.

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
    """
    Skew sextupole magnet element.

    The strength is applied to the ``PolynomA[2]`` component of the underlying lattice element, the
    field component used for correcting coupled chromatic effects. Strengths are expressed in
    ``m-2`` and converted to power-converter values by the attached magnet model.

    Parameters
    ----------
    name : str
        Element name.
    model : MagnetModel | None, optional
        Magnet model used to convert between strength and hardware value, and to
        resolve the underlying control-system device names.
    lattice_names : str | None, optional
        Name or names of the matching element(s) in the simulated lattice. Defaults
        to ``name``.
    description : str | None, optional
        Human-readable description of the magnet.

    See Also
    --------
    Magnet : Base class listing the strength and hardware accessors.
    """

    polynom = PolynomInfo("PolynomA", 2)

    def __init__(
        self, name: str, model: MagnetModel | None = None, lattice_names: str | None = None, description: str | None = None
    ):
        """
        Initialize the SkewSext.

        Parameters
        ----------
        name : str
            Element name.
        model : MagnetModel | None
            Magnet model used to convert between strength and hardware value, and to resolve the underlying
            control-system device names.
        lattice_names : str | None
            Name or names of the matching element(s) in the simulated lattice. Defaults to ``name``.
        description : str | None
            Human-readable description of the magnet.
        """
        super().__init__(name, model, lattice_names, description)
