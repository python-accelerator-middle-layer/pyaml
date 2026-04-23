from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .exception import PyAMLException

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder

# TODO: this needs to be changed since no _cfg anymore
# def __pyaml_repr__(obj):
#     """
#     Returns a string representation of a pyaml object
#     """
#     if hasattr(obj, "_cfg"):
#         if isinstance(obj, Element):
#             return repr(obj._cfg).replace(
#                 "ConfigModel(",
#                 obj.__class__.__name__ + "(peer='" + obj.get_peer_name() + "', ",
#             )
#         else:
#             # no peer
#             return repr(obj._cfg).replace("ConfigModel", obj.__class__.__name__)
#     else:
#         # Object is not yet fully constructed
#         if isinstance(obj, Element):
#             return f"{obj.__class__.__name__}: {obj.get_name()}"
#         else:
#             return f"{obj.__class__.__name__}"


class ElementSchema(BaseModel):
    """
    Base schema for element configuration.

    Parameters
    ----------
    name : str
        The name of the PyAML element.
    description : str, optional
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

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Name of the element")
    description: str | None = Field(default=None, description="Description of the element.")
    lattice_names: str | None = Field(
        default=None, description="The name(s) of the associated element(s) in the lattice."
    )

    # Validate the syntax for the lattice_names field
    # This validation is currently very basic and can be improved
    @field_validator("lattice_names")
    @classmethod
    def validate_lattice_names(cls, v):
        if v is None:
            return v

        # Example: very simplified checks
        if v.startswith("list(") and v.endswith(")"):
            return v
        if "@" in v:
            return v
        if "#" in v and ".." in v:
            return v
        raise ValueError("Invalid lattice_names syntax")


class Element:
    """
    Class providing access to one element of a physical or simulated lattice

    Attributes:
      name: str
        The unique name identifying the element in the configuration file
      description : str, optional
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

    def __init__(self, name: str, description: str | None = None, lattice_names: str | None = None):
        self._name: str = name
        self._description = description
        self._lattice_names = lattice_names
        self._peer: "ElementHolder" = None  # Peer: ControlSystem, Simulator

    def get_name(self) -> str:
        """
        Returns the name of the element
        """
        return self._name

    def get_lattice_names(self) -> str:
        """
        Returns the name of associated lattice element(s)
        """
        if not self._lattice_names:
            return self._name
        else:
            return self._lattice_names

    def get_description(self) -> str:
        """
        Returns the description of the element
        """
        return self._description

    def set_energy(self, E: float):
        """
        Set the instrument energy on this element
        """
        pass

    def set_mcf(self, alphac: float):
        """
        Set the instrument moment compaction factor on this element
        """
        pass

    def set_harmonic(self, h: int):
        """
        Sets the harmonic number (number of bucket) on this element
        """
        pass

    def check_peer(self):
        """
        Throws an exception if the element is not attacched
        to a simulator or to a control system
        """
        if self._peer is None:
            raise PyAMLException(f"{str(self)} is not attachedto a control system or the a simulator")

    @property
    def peer(self) -> "ElementHolder":
        """
        Returns the peer simulator or control system
        """
        return self._peer

    def get_peer_name(self) -> str:
        """
        Returns a string representation of peer simulator or control system
        """
        return "None" if self._peer is None else f"{self._peer.__class__.__name__}:{self._peer.name()}"

    def post_init(self):
        """
        Method triggered after all initialisations are done
        """
        pass


#    def __repr__(self):
#        return __pyaml_repr__(self)
