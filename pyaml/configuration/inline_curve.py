from ..configuration import get_root_folder
from ..common.exception import PyAMLException
from .curve import Curve

from pathlib import Path
from pydantic import BaseModel,ConfigDict
import numpy as np


# Define the main class name for this module
PYAMLCLASS = "InlineCurve"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    mat: list[list[float]]
    """CSV file that contains the curve (n rows,2 columns)"""

class InlineCurve(Curve):
    """
    Class for load CSV (x,y) curve
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        # Load the curve
        self._curve = np.array(self._cfg.mat)

        _s = np.shape(self._curve)
        if len(_s) != 2 or _s[1] != 2:
            raise PyAMLException(f"InlineCurve(mat='{cfg.mat}',dtype=float): wrong shape (2,2) expected but got {str(_s)}")

    def get_curve(self) -> np.array:
        return self._curve

    def __repr__(self):
       return repr(self._cfg).replace("ConfigModel",self.__class__.__name__)
