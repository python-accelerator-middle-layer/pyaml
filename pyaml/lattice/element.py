from pydantic import BaseModel,ConfigDict

class ElementModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

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
    
    # TODO: _repr_ is used for identifying element in various array. Use a get_id() method instead
    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            self.name
        )
