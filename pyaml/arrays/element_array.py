from ..common.element import Element
from ..common.exception import PyAMLException

def get_peer_from_array(array):
    """
    Returns the peer (Simulator or ControlSystem) of an element list
    """
    peer = array[0]._peer if len(array)>0 else None
    if peer is None or any([m._peer!=peer for m in array]):
        raise PyAMLException(f"{array.__class__.__name__} {array.get_name()}:  All elements must be attached to the same instance of either a Simulator or a ControlSystem")
    return peer

class ElementArray(list[Element]):
    """
    Class that implements access to a magnet array
    """

    def __init__(self,arrayName:str,elements:list[Element]):
        """
        Construct an element array

        Parameters
        ----------
        arrayName : str
            Array name
        elements: list[Element]
            Element list, all elements must be attached to the same instance of 
            either a Simulator or a ControlSystem.
        """
        super().__init__(i for i in elements)
        self.__name = arrayName
        holder = get_peer_from_array(self)
        self.__name = arrayName

    def get_name(self) -> str:
        return self.__name

    def names(self) -> list[str]:
        return [e.get_name() for e in self]


    


    