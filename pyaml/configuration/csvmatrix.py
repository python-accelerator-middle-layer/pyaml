"""
Class for load CSV matrix
"""
from pydantic import BaseModel,Field
from ..configuration import get_root_folder
from pathlib import Path

import numpy as np

from .matrix import Matrix

# Define the main class name for this module
PYAMLCLASS = "CSVMatrix"

class ConfigModel(BaseModel):

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
