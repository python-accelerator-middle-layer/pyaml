from pydantic import BaseModel
from ..configuration.factory import register_element
from ..lattice.simulator import Simulator
from .controlsystem import ControlSystem

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
        self.target: Simulator|ControlSystem|None = None
        register_element(self)

    def set_energy(self,E:float):
        pass

    def set_target(self,target:Simulator|ControlSystem):
        self.target = target

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            self.name
        )
