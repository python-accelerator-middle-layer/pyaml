"""
Class for load CSV (x,y) curve
"""
from pydantic import BaseModel

import numpy as np

from .Curve import Curve

class Config(BaseModel):

    file: str

class CSVCurve(Curve):

    def __init__(self, cfg: Config):
        self._cfg = cfg

        # Load CSV curve
        self._curve = np.genfromtxt(cfg.file, delimiter=",", dtype=float)
        s = np.shape(self._curve)
        if len(s) != 2 or s[1] != 2:
            raise Exception(cfg.file + " wrong dimension")

    def get_curve(self) -> np.array:
        return self._curve
