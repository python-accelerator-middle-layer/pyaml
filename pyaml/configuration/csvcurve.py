from ..configuration import get_root_folder
from ..common.exception import PyAMLException
from .curve import Curve

from pathlib import Path
from pydantic import BaseModel,ConfigDict
import numpy as np


# Define the main class name for this module
PYAMLCLASS = "CSVCurve"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    file: str
    """CSV file that contains the curve (n rows,2 columns)"""

class CSVCurve(Curve):
    """
    Class for load CSV (x,y) curve
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

        # Load CSV curve
        path:Path = get_root_folder() / cfg.file
        try:
            self._curve = np.genfromtxt(path, delimiter=",", dtype=float, loose=False)
        except ValueError as e:
            raise PyAMLException(f"CSVCurve(file='{cfg.file}',dtype=float): {str(e)}") from None

        _s = np.shape(self._curve)
        if len(_s) != 2 or _s[1] != 2:
            raise PyAMLException(f"CSVCurve(file='{cfg.file}',dtype=float): wrong shape (2,2) expected but got {str(_s)}")

    def get_curve(self) -> np.array:
        return self._curve

    def __repr__(self):
       return repr(self._cfg).replace("ConfigModel",self.__class__.__name__)
