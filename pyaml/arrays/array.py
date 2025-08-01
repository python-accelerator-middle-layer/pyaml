"""
Magnet array configuration
"""

import numpy as np
from pydantic import BaseModel
from ..lattice.element_holder import ElementHolder

class ArrayModel(BaseModel):

    name: str
    """Family name"""
    elements: list[str]
    """List of pyaml element names"""

class Array(object):
    """
    Class that implements access to arrays (families)
    """

    def __init__(self, cfg: ArrayModel):
        self._cfg = cfg

    def fill_array(self,holder:ElementHolder):
        raise "Array.fill_array() is not subclassed"
                    
            
        
