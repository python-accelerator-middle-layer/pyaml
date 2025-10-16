from pydantic import BaseModel,ConfigDict

class ElementConfigModel(BaseModel):

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
        self.__name: str = name

    def get_name(self):
        """
        Returns the name of the element
        """
        return self.__name

    def set_energy(self,E:float):
        pass
        
    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            self.__name
        )
