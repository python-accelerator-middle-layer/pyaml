"""
Class for load CSV matrix
"""
from pydantic import BaseModel,ConfigDict
from ..configuration import get_root_folder
from pathlib import Path

import numpy as np

from .matrix import Matrix

# Define the main class name for this module
PYAMLCLASS = "CSVMatrix"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    file: str
    """CSV file that contains the matrix"""

class CSVMatrix(Matrix):

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        # Load CSV matrix
        path:Path = get_root_folder() / cfg.file
        self._mat = np.genfromtxt(path, delimiter=",", dtype=float)

    def get_matrix(self) -> np.array:
        return self._mat
