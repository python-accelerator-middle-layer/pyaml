from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict

from ..common.exception import PyAMLException
from ..configuration.fileloader import get_path
from .curve import Curve, CurveSchema


class CSVCurveSchema(CurveSchema):
    """
    Configuration model for CSV curve

    Parameters
    ----------
    file : str
        CSV file that contains the curve (n rows, 2 columns)
    """

    model_config = ConfigDict(extra="forbid")

    file: str


class CSVCurve(Curve):
    """
    Class for load CSV (x,y) curve
    """

    def __init__(self, file: str):
        self._file = file

        # Load CSV curve
        path = get_path(self._file)
        try:
            self._curve = np.genfromtxt(path, delimiter=",", dtype=float, loose=False)
        except ValueError as e:
            raise PyAMLException(f"CSVCurve(file='{self._file}',dtype=float): {str(e)}") from None

        _s = np.shape(self._curve)
        if len(_s) != 2 or _s[1] != 2:
            raise PyAMLException(
                f"CSVCurve(file='{self._file}',dtype=float):wrong shape (2,2) expected but got {str(_s)}"
            )

    def get_curve(self) -> np.array:
        """
        Get the curve data.

        Returns
        -------
        np.array
            Curve data as a 2D numpy array of shape (n, 2)
        """
        return self._curve


#    def __repr__(self):
#        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
