from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict

from ..common.exception import PyAMLException
from ..configuration.fileloader import get_path
from .matrix import Matrix, MatrixSchema


class CSVMatrixSchema(MatrixSchema):
    """
    Configuration model for CSV matrix

    Parameters
    ----------
    file : str
        CSV file that contains the matrix
    """

    model_config = ConfigDict(extra="forbid")

    file: str


class CSVMatrix(Matrix):
    """
    Class for loading CSV matrix
    """

    def __init__(self, file: str):
        self._file = file

        # Load CSV matrix
        path = get_path(self._file)
        try:
            self._mat = np.genfromtxt(path, delimiter=",", dtype=float, loose=False)
        except ValueError as e:
            raise PyAMLException(f"CSVMatrix(file='{self._file}',dtype=float): {str(e)}") from None

    def get_matrix(self) -> np.array:
        """
        Get the matrix data.

        Returns
        -------
        np.array
            Matrix data as a numpy array
        """
        return self._mat


#    def __repr__(self):
#        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
