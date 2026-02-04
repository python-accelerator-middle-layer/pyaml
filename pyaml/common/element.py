from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from .exception import PyAMLException

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder


def __pyaml_repr__(obj):
    """
    Returns a string representation of a pyaml object
    """
    if hasattr(obj, "_cfg"):
        if isinstance(obj, Element):
            return repr(obj._cfg).replace(
                "ConfigModel(",
                obj.__class__.__name__ + "(peer='" + obj.get_peer() + "', ",
            )
        else:
            # no peer
            return repr(obj._cfg).replace("ConfigModel", obj.__class__.__name__)
    else:
        # Object is not yet fully constructed
        if isinstance(obj, Element):
            return f"{obj.__class__.__name__}: {obj.get_name()}"
        else:
            return f"{obj.__class__.__name__}"


class ElementConfigModel(BaseModel):
    """
    Base class for element configuration.

    Parameters
    ----------
    name : str
        The name of the PyAML element.
    description : str
        Description of the element.
    lattice_names : str or None, optional
        The name(s) of the associated element(s) in the lattice. By default,
        the PyAML element name is used. lattice_name accept the following
        syntax:
        - list(name,[name]) : Element names
        - [name]@idx[,idx] : Element indices in the subset formed by name.
        - [name]#start_idx..end_idx : Element range in the subset formed by name.
        In the above syntax, if the name is not specficied, the whole set
        of lattice element is used for indexing.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    description: str | None = None
    lattice_names: str | None = None


class Element(object):
    """
    Class providing access to one element of a physical or simulated lattice

    Attributes:
      name: str
        The unique name identifying the element in the configuration file
    """

    def __init__(self, name: str):
        self.__name: str = name
        self._peer: "ElementHolder" = None  # Peer: ControlSystem, Simulator

    def get_name(self) -> str:
        """
        Returns the name of the element
        """
        return self.__name

    def get_lattice_names(self) -> str:
        """
        Returns the name of associated lattice element(s)
        """
        if not hasattr(self, "_cfg"):
            return self.__name
        else:
            return self._cfg.lattice_names

    def get_descripton(self) -> str:
        """
        Returns the description of the element
        """
        return self._cfg.description

    def set_energy(self, E: float):
        """
        Set the instrument energy on this element
        """
        pass

    def check_peer(self):
        """
        Throws an exception if the element is not attacched
        to a simulator or to a control system
        """
        if self._peer is None:
            raise PyAMLException(
                f"{str(self)} is not attachedto a control system or the a simulator"
            )

    def get_peer(self) -> str:
        """
        Returns a string representation of peer simulator or control system
        """
        return (
            "None"
            if self._peer is None
            else f"{self._peer.__class__.__name__}:{self._peer.name()}"
        )

    def post_init(self):
        """
        Method triggered after all initialisations are done
        """
        pass

    def __repr__(self):
        return __pyaml_repr__(self)
