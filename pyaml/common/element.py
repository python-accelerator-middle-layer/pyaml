from .exception import PyAMLException

from pydantic import BaseModel,ConfigDict

class ElementConfigModel(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")

    name : str
    """Element name"""

class Element(object):
    """
    Class providing access to one element of a physical or simulated lattice

    Attributes:
      name: str
        The unique name identifying the element in the configuration file
    """
    def __init__(self,name:str):
        self.__name: str = name
        self._peer = None # Peer: ControlSystem, Simulator

    def get_name(self):
        """
        Returns the name of the element
        """
        return self.__name

    def set_energy(self,E:float):
        """
        Set the instrument energy on this element
        """
        pass

    def check_peer(self):
        """
        Throws an exception if the element is not attacched to a simulator or to a control system
        """
        if self._peer is None:
            raise PyAMLException(f"{str(self)} is not attached to a control system or the a simulator")
        
    def get_peer(self) -> str:
        """
        Returns a string representation of peer simulator or control system
        """
        return "None" if self._peer is None else f"{self._peer.__class__.__name__}:{self._peer.name()}"
 
    def __repr__(self):
        return "%s(name='%s', peer='%s')" % (
            self.__class__.__name__,
            self.__name,
            self.get_peer()
        )
