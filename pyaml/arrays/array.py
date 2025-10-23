"""
Magnet array configuration
"""

import numpy as np
from pydantic import BaseModel,ConfigDict
from ..lattice.element_holder import ElementHolder
from ..control.controlsystem import ControlSystem

class ArrayConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    name: str
    """Family name"""
    elements: list[str]
    """List of pyaml element names"""

class ArrayConfig(object):
    """
    Class that implements configuration for access to arrays (families)
    """
    def __init__(self, cfg: ArrayConfigModel):
        self._cfg = cfg

    def fill_array(self,holder:ElementHolder):
        raise "Array.fill_array() is not subclassed"

    def init_aggregator(self,cs:ControlSystem):
        raise "Array.init_aggregator() is not subclassed"

