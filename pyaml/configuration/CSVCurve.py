"""
Class for load CSV (x,y) curve
"""

from pathlib import Path

import numpy as np

from .Curve import Curve
from ..configuration.models import ConfigBase, get_config_file_path


class Config(ConfigBase):
    file: str | Path


class CSVCurve(Curve):

    def __init__(self, cfg: Config):
        self._cfg = cfg

        path = get_config_file_path(cfg.file)

        # Load CSV curve
        self.curve = np.genfromtxt(path, delimiter=",", dtype=float)
        s = np.shape(self.curve)
        if len(s) != 2 or s[1] != 2:
            raise Exception(cfg.file + " wrong dimension")

    def get_curve(self) -> np.array:
        return self.curve
