from abc import ABCMeta, abstractmethod

from numpy import array
from pydantic import BaseModel, ConfigDict


class MatrixSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Matrix(metaclass=ABCMeta):
    """
    Abstract class providing access to a matrix
    """

    @abstractmethod
    def get_matrix(self) -> array:
        """Returns the matrix"""
        pass
