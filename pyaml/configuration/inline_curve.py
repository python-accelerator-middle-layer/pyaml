from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict

from ..common.exception import PyAMLException
from ..configuration import get_root_folder
from .curve import Curve

# Define the main class name for this module
PYAMLCLASS = "InlineCurve"


class ConfigModel(BaseModel):
    """
    Configuration model for inline curve

    Parameters
    ----------
    mat : list[list[float]]
        Curve data (n rows, 2 columns)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    mat: list[list[float]]


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
            raise PyAMLException(
                f"InlineCurve(mat='{cfg.mat}',dtype=float): wrong shape (2,2) expected but got {str(_s)}"
            )

    def get_curve(self) -> np.array:
        return self._curve

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
