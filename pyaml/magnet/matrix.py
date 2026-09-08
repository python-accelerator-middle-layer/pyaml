"""
Magnet response matrices.

This module defines matrix representations used by magnet models.
"""

from abc import ABCMeta, abstractmethod

from numpy import array


class Matrix(metaclass=ABCMeta):
    """
    Abstract class providing access to a matrix

    Methods
    -------
    get_matrix()
        Returns the matrix
    """

    @abstractmethod
    def get_matrix(self) -> array:
        """Returns the matrix"""
        pass
