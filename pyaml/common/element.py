import warnings
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .exception import PyAMLException
from .utils import __pyaml_repr__

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder


class ElementSchema(BaseModel):
    """
    Base schema for element configuration.

    Parameters
    ----------
    name : str
        The name of the element.
    description : str, optional
        Description of the element.
    lattice_names : str or None, optional
        The name(s) of the associated element(s) in the lattice. By default,
        the element name is used. lattice_name accept the following
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

    Parameters
    ----------
    name : str
        The name of the element.
    description : str, optional
        Description of the element.
    lattice_names : str or None, optional
        The name(s) of the associated element(s) in the lattice. By default,
        the element name is used. lattice_name accept the following
        syntax:
        - list(name,[name]) : Element names
        - [name]@idx[,idx] : Element indices in the subset formed by name.
        - [name]#start_idx..end_idx : Element range in the subset formed by name.
        In the above syntax, if the name is not specficied, the whole set
        of lattice element is used for indexing.
    """

    def __init__(self, name: str, description: str | None = None, lattice_names: str | None = None):
        self._name: str = name
        self.description = description

        # If no lattice names are given put it to the name of the element
        if lattice_names:
            self._lattice_names = lattice_names
        else:
            self._lattice_names = self._name

        self._peer: ElementHolder | None = None  # Peer: ControlSystem, Simulator

    @property
    def name(self) -> str:
        return self._name

    # TODO: implement name setter -> this requires checking so the name is unique

    def get_name(self) -> str:
        warnings.warn(
            "get_name() is deprecated; use .name instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.name

    @property
    def lattice_names(self) -> str:
        return self._lattice_names

    # TODO: implement lattice_names setter -> this requires validation of the format

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
            raise PyAMLException(f"{str(self)} is not attached to a control system or a simulator.")

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

    def __repr__(self):
        return __pyaml_repr__(self)
