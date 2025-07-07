import numpy as np
from pydantic import BaseModel


# Define the main class name for this module
PYAMLCLASS = "Array"

class ConfigModel(BaseModel):

    name: str
    """Family name"""
    elements: list[str]
    """List of pyaml element names"""

class Array(object):
    """
    Class that implements access to arrays (families)
    """

    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg
