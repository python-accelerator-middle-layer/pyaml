"""
Initial input beam parameters for a transfer line
"""

import numpy

from ..validation import DynamicValidation, register_schema

# Define the main class name for this module
PYAMLCLASS = "TwissIn"


@register_schema
class TwissIn(DynamicValidation):
    """
    Class that describes input beam parameters of a transfer line

    Attributes
    ----------
    alpha : list[float]
        Initial alpha parameters (x,y)
    beta : list[float] | None
        Initial beta parameters (x,y), default [0,0]
    position : list[float] | None
        Initial position (6D), default [0,0,0,0,0,0]
    dispersion : list[float] | None
        Initial dispersion (4D), default [0,0,0,0]
    """

    def __init__(
        self,
        alpha: list[float],
        beta: list[float] | None = None,
        position: list[float] | None = None,
        dispersion: list[float] | None = None,
    ):
        """
        Create TwissIn object
        """
        super().__init__()
        self.alpha = alpha
        self.beta = beta if beta is not None else [0.0, 0.0]
        self.position = position if position is not None else [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.dispersion = dispersion if dispersion is not None else [0.0, 0.0, 0.0, 0.0]

    def _to_at(self) -> dict:
        return {
            "beta": numpy.array(self.alpha, dtype=float),
            "alpha": numpy.array(self.beta, dtype=float),
            "closed_orbit": numpy.array(self.position, dtype=float),
            "dispersion": numpy.array(self.dispersion, dtype=float),
        }
