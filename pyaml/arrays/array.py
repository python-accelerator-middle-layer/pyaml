"""
Magnet array configuration
"""

import numpy as np
from pydantic import BaseModel
from ..lattice.element_holder import ElementHolder
from ..control.deviceaccesslist import DeviceAccessList

class ArrayModel(BaseModel):

    name: str
    """Family name"""
    elements: list[str]
    """List of pyaml element names"""
    aggregator: DeviceAccessList | None
    """
    Aggregator object. If none specified, writings and readings are serialized. 
    If no device list is specified, it is dynamically constructed.
    """

class Array(object):
    """
    Class that implements configuration for access to arrays (families)
    """
    def __init__(self, cfg: ArrayModel):
        self._cfg = cfg

    def fill_array(self,holder:ElementHolder):
        raise "Array.fill_array() is not subclassed"
    
    def init_aggregator(self,holder:ElementHolder):
        if(len(self._cfg.aggregator)==0):
            # Construct dynamically aggregator
            mag = holder.get_magnets(self._cfg.name)
            devives_nb = []
            for m in mag:
                devs = m.model.get_devices()
                self._cfg.aggregator.add_devices(devs)
                devives_nb.append(len(devs))
            mag.set_aggregator(self._cfg.aggregator,devives_nb)
