from abc import ABCMeta, abstractmethod
from numpy import array
from pydantic import BaseModel

class Matrix(BaseModel,metaclass=ABCMeta):
    """
    Abstract class providing access to a matrix
    """
    @abstractmethod
    def get_matrix(self) -> array:
        """Returns the matrix"""
        pass
