from ..configuration import get_root_folder
from .matrix import Matrix
from ..common.exception import PyAMLException

from pydantic import BaseModel,ConfigDict
from pathlib import Path
import numpy as np


# Define the main class name for this module
PYAMLCLASS = "CSVMatrix"

class ConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    file: str
    """CSV file that contains the matrix"""

class CSVMatrix(Matrix):
    """
    Class for loading CSV matrix
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        # Load CSV matrix
        path:Path = get_root_folder() / cfg.file
        try:
            self._mat = np.genfromtxt(path, delimiter=",", dtype=float, loose=False)
        except ValueError as e:
            raise PyAMLException(f"CSVMatrix(file='{cfg.file}',dtype=float): {str(e)}") from None

    def get_matrix(self) -> np.array:
        return self._mat

    def __repr__(self):
       return repr(self._cfg).replace("ConfigModel",self.__class__.__name__)
