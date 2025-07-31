from abc import ABCMeta, abstractmethod
from numpy import array

class Matrix(metaclass=ABCMeta):
    """
    Abstract class providing access to a matrix
    """
    @abstractmethod
    def get_matrix(self) -> array:
        """Returns the matrix"""
        pass
