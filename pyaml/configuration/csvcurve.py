"""
Class for load CSV (x,y) curve
"""
from pydantic import BaseModel,Field

import numpy as np

from .curve import Curve

# Define the main class name for this module
PYAMLCLASS = "CSVCurve"

class ConfigModel(BaseModel):

    file: str
    """CSV file that contains the curve (n rows,2 columns)"""

class CSVCurve(Curve):

    def __init__(self, cfg: ConfigModel):

        # Load CSV curve
        self._curve = np.genfromtxt(cfg.file, delimiter=",", dtype=float)
        s = np.shape(self._curve)
        if len(s) != 2 or s[1] != 2:
            raise Exception(cfg.file + " wrong dimension")

    def get_curve(self) -> np.array:
        return self._curve
