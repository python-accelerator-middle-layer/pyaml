"""
Class for load CSV matrix
"""
from pydantic import BaseModel,Field

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
        self._mat = np.genfromtxt(cfg.file, delimiter=",", dtype=float)

    def get_matrix(self) -> np.array:
        return self._mat
