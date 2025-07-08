from .array import ArrayModel
from .array import Array

# Define the main class name for this module
PYAMLCLASS = "HCorrector"

class ConfigModel(ArrayModel):
    pass

class HCorrector(Array):
    """
    Class that implements access to arrays (families)
    """
    def __init__(self, cfg: ArrayModel):
        super().__init__(cfg)
