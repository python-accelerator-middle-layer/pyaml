"""
Magnet array configuration
"""

from pydantic import BaseModel, ConfigDict

from pyaml.common.exception import PyAMLException

from ..common.element_holder import ElementHolder


class ArrayConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

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

    def fill_array(self, holder: ElementHolder):
        raise PyAMLException("Array.fill_array() is not subclassed")
