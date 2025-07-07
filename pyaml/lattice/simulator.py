import numpy as np
from pydantic import BaseModel


# Define the main class name for this module
PYAMLCLASS = "Simulator"

class ConfigModel(BaseModel):

    name: str
    """Simulator name"""
    lattice: str
    """AT lattice file"""

class Simulator(object):
    """
    Class that implements access to AT simulator
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
