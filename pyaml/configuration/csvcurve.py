"""
Class for load CSV (x,y) curve
"""
from pydantic import BaseModel,Field
from ..configuration import get_root_folder
from pathlib import Path

import numpy as np

from .curve import Curve

# Define the main class name for this module
PYAMLCLASS = "CSVCurve"

class ConfigModel(BaseModel):

    file: str
    """CSV file that contains the curve (n rows,2 columns)"""

class CSVCurve(Curve):

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

        # Load CSV curve
        path:Path = get_root_folder() / cfg.file
        self._curve = np.genfromtxt(path, delimiter=",", dtype=float)
        _s = np.shape(self._curve)
        if len(_s) != 2 or _s[1] != 2:
            raise Exception(cfg.file + " wrong dimension")

    def get_curve(self) -> np.array:
        return self._curve
