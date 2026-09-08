"""
Magnet response matrices.

This module defines matrix representations used by magnet models.
"""

import numpy as np
from numpy.typing import NDArray

from ..common.element import __pyaml_repr__
from ..common.exception import PyAMLException
from ..configuration.fileloader import ROOT
from ..validation import DynamicValidation, register_schema
from .matrix import Matrix

# Define the main class name for this module
PYAMLCLASS = "CSVMatrix"


@register_schema
class CSVMatrix(Matrix, DynamicValidation):
    """
    Matrix loaded from a CSV file.

    This class reads a CSV file containing numeric values and stores the
    resulting matrix as a NumPy array.

    Parameters
    ----------
    file : str
        Path to the CSV file. Relative paths are resolved using the
        project's configured root directory.

    Raises
    ------
    PyAMLException
        If the CSV file cannot be parsed as a numeric array.
    """

    def __init__(self, file: str):
        """
        Initialize the CSVMatrix.

        Parameters
        ----------
        file : str
            Path to the CSV file. Relative paths are resolved using the project's configured root directory.
        """
        self._file = file

        # Load CSV matrix
        path = ROOT.expand_path(self._file)
        try:
            self._mat = np.genfromtxt(path, delimiter=",", dtype=float, loose=False)
        except ValueError as e:
            raise PyAMLException(f"CSVMatrix(file='{self._file}',dtype=float): {str(e)}") from None

    @property
    def file(self):
        """Return the configured CSV file path."""
        return self._file

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
