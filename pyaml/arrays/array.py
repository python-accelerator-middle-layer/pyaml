"""
Magnet array configuration
"""

import numpy as np
from pydantic import BaseModel,ConfigDict
from ..lattice.element_holder import ElementHolder
from ..control.deviceaccesslist import DeviceAccessList

class ArrayConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    name: str
    """Family name"""
    elements: list[str]
    """List of pyaml element names"""
    aggregator: DeviceAccessList | None = None
    """
    Aggregator object. If none specified, writings and readings are serialized. 
    If no device list is specified, it is dynamically constructed.
    """

class ArrayConfig(object):
    """
    Class that implements configuration for access to arrays (families)
    """
    def __init__(self, cfg: ArrayConfigModel):
        self._cfg = cfg

    def fill_array(self,holder:ElementHolder):
        raise "Array.fill_array() is not subclassed"

    def init_aggregator(self,holder:ElementHolder):
        raise "Array.init_aggregator() is not subclassed"

