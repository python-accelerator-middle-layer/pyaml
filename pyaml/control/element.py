from pydantic import BaseModel
from ..configuration.factory import register_element

class ElementModel(BaseModel):

    name : str
    """Element name"""

class Element(object):
    """
    Class providing access to one element of a physical or simulated lattice

    Attributes:
    name (str): The name identifying the element in the configuration file
    """
    def __init__(self,name:str):
        self.name = name
        register_element(name,self)

    def __repr__(self):
        return "%s(name=%s)" % (
            self.__class__.__name__,
            self.name
        )
