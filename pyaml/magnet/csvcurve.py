"""CSV-backed magnet excitation curves.

This module loads two-column excitation data from CSV files for magnet-model
calibration and interpolation.
"""

import numpy as np
from numpy.typing import NDArray

from ..common.element import __pyaml_repr__
from ..common.exception import PyAMLException
from ..configuration.fileloader import ROOT
from ..validation import DynamicValidation, register_schema
from .curve import Curve

# Define the main class name for this module
PYAMLCLASS = "CSVCurve"


@register_schema
class CSVCurve(Curve, DynamicValidation):
    """
    Curve loaded from a CSV file.

    This class reads a CSV file containing a two-column numeric dataset
    representing ``(x, y)`` coordinate pairs. The file is loaded during
    initialization and stored internally as a NumPy array.

    The CSV file must:

    - contain exactly two columns,
    - use commas as the delimiter,
    - contain values that can be converted to ``float``.

    Parameters
    ----------
    file : str
        Path to the CSV file. Relative paths are resolved using the
        project's configured root directory.

    Attributes
    ----------
    file : str
        Path to the CSV file provided during initialization.

    Raises
    ------
    PyAMLException
        If the file cannot be parsed as a numeric CSV or if the loaded
        data does not have shape ``(n, 2)``.

    Notes
    -----
    The loaded curve is stored internally as a NumPy array with shape
    ``(n, 2)``, where the first column contains x-values and the second
    column contains y-values. The data can be accessed using
    :meth:`get_curve`.
    """

    def __init__(self, file: str):
        """
        Initialize the CSVCurve.

        Parameters
        ----------
        file : str
            Input value for this operation.
        """
        self._file = file

        # Load CSV curve
        path = ROOT.expand_path(self._file)
        try:
            self._curve = np.genfromtxt(path, delimiter=",", dtype=float, loose=False)
        except ValueError as e:
            raise PyAMLException(f"CSVCurve(file='{self._file}',dtype=float): {str(e)}") from None

        _s = np.shape(self._curve)
        if len(_s) != 2 or _s[1] != 2:
            raise PyAMLException(f"CSVCurve(file='{self._file}',dtype=float):wrong shape (2,2) expected but got {str(_s)}")

    @property
    def file(self):
        """Return the configured CSV file path."""
        return self._file

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
