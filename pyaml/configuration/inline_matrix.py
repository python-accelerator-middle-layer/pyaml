import numpy as np
from pydantic import BaseModel, ConfigDict

from .matrix import Matrix

# Define the main class name for this module
PYAMLCLASS = "InlineMatrix"


class ConfigModel(BaseModel):
    """
    Configuration model for inline matrix

    Parameters
    ----------
    mat : list[list[float]]
        The matrix
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    mat: list[list[float]]


class InlineMatrix(Matrix):
    """
    Class for loading CSV matrix
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
        # Load the matrix
        self._mat = np.array(self._cfg.mat)

    def get_matrix(self) -> np.array:
        return self._mat

    def __repr__(self):
        return repr(self._cfg).replace("ConfigModel", self.__class__.__name__)
