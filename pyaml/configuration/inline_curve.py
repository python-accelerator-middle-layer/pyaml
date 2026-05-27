from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict

from ..common.exception import PyAMLException
from ..configuration import get_root_folder
from .curve import Curve, CurveSchema


class InlineCurveSchema(CurveSchema):
    """
    Configuration model for inline curve

    Parameters
    ----------
    mat : list[list[float]]
        Curve data (n rows, 2 columns)
    """

    model_config = ConfigDict(extra="forbid")

    mat: list[list[float]]


class InlineCurve(Curve):
    """
    Class for load CSV (x,y) curve
    """

    def __init__(self, mat: list[list[float]]):
        self._mat = mat

        # Load the curve
        self._curve = np.array(self._mat)

        _s = np.shape(self._curve)
        if len(_s) != 2 or _s[1] != 2:
            raise PyAMLException(f"InlineCurve(mat='{self._mat}',dtype=float): wrong shape (2,2) expected but got {str(_s)}")

    def get_curve(self) -> np.array:
        """
        Get the curve data.

        Returns
        -------
        np.array
            Curve data as a 2D numpy array of shape (n, 2)
        """
        return self._curve


#   def __repr__(self):
#       return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
