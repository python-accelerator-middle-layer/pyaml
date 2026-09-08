"""
In-memory magnet excitation curves.

This module validates and exposes two-column excitation data supplied directly
as Python sequences.
"""

import numpy as np
from numpy.typing import NDArray

from ..common.element import __pyaml_repr__
from ..common.exception import PyAMLException
from ..validation import DynamicValidation, register_schema
from .curve import Curve

# Define the main class name for this module
PYAMLCLASS = "InlineCurve"


@register_schema
class InlineCurve(Curve, DynamicValidation):
    """
    Curve defined directly from an in-memory matrix of (x, y) points.

    This class stores curve data provided as a list of rows, where each row must
    contain exactly two values: the x-coordinate and the y-coordinate. The data is
    converted to a NumPy array and validated to ensure it has shape ``(n, 2)``.

    Parameters
    ----------
    mat : list[list[float]]
        Curve data as a two-column matrix. Each row represents one point in the
        curve, with ``mat[i][0]`` being the x-value and ``mat[i][1]`` being the
        y-value.

    Attributes
    ----------
    mat
        Return the original in-memory curve point matrix.

    Methods
    -------
    get_curve()
        Get the curve data.

    Raises
    ------
    PyAMLException
        If the provided matrix does not have two columns.
    """

    def __init__(self, mat: list[list[float]]):
        """
        Initialize the InlineCurve.
        """
        self._mat = mat

        # Load the curve
        self._curve = np.array(self._mat)

        _s = np.shape(self._curve)
        if len(_s) != 2 or _s[1] != 2:
            raise PyAMLException(f"InlineCurve(mat='{self._mat}',dtype=float): wrong shape (2,2) expected but got {str(_s)}")

    @property
    def mat(self):
        """Return the original in-memory curve point matrix."""
        return self._mat

    def get_curve(self) -> NDArray[np.float64]:
        """
        Get the curve data.

        Returns
        -------
        np.array
            Curve data as a 2D numpy array of shape (n, 2)
        """
        return self._curve

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
