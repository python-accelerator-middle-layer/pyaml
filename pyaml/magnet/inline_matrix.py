"""
Magnet response matrices.

This module defines matrix representations used by magnet models.
"""

import numpy as np
from numpy.typing import NDArray

from ..common.element import __pyaml_repr__
from ..validation import DynamicValidation, register_schema
from .matrix import Matrix

# Define the main class name for this module
PYAMLCLASS = "InlineMatrix"


@register_schema
class InlineMatrix(Matrix, DynamicValidation):
    """
    Matrix defined directly from in-memory data.

    Parameters
    ----------
    mat : list[list[float]]
        Matrix data given as a nested list of numbers.

    Attributes
    ----------
    _mat : np.ndarray
        Internal NumPy representation of the matrix.
    """

    def __init__(self, mat: list[list[float]]):
        # Load the matrix
        """
        Initialize the InlineMatrix.

        Parameters
        ----------
        mat : list[list[float]]
            Matrix data given as a nested list of numbers.
        """
        self._mat = np.array(mat)

    @property
    def mat(self):
        """Return the original in-memory magnet matrix."""
        return self._mat

    def get_matrix(self) -> NDArray[np.float64]:
        """
        Get the matrix data.

        Returns
        -------
        np.array
            Matrix data as a numpy array
        """
        return self._mat

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
