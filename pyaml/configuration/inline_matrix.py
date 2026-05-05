import numpy as np
from pydantic import BaseModel, ConfigDict

from .matrix import Matrix, MatrixSchema


class InlineMatrixSchema(MatrixSchema):
    """
    Configuration model for inline matrix

    Parameters
    ----------
    mat : list[list[float]]
        The matrix
    """

    model_config = ConfigDict(extra="forbid")

    mat: list[list[float]]


class InlineMatrix(Matrix):
    """
    Class for loading CSV matrix
    """

    def __init__(self, mat: list[list[float]]):
        self._mat = mat

        # Load the matrix
        self._matrix = np.array(self._mat)

    def get_matrix(self) -> np.array:
        """
        Get the matrix data.

        Returns
        -------
        np.array
            Matrix data as a numpy array
        """
        return self._matrix


#    def __repr__(self):
#        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
