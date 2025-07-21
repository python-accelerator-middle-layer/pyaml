from pydantic import BaseModel

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
        self.name: str = name

    def set_energy(self,E:float):
        pass

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            self.name
        )
