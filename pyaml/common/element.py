import warnings
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from ..validation.validator import add_schema
from .exception import PyAMLException

if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder


# def __pyaml_repr__(obj):
#     """
#     Returns a string representation of a pyaml object
#     """
#     if hasattr(obj, "_cfg"):
#         if isinstance(obj, Element):
#             return repr(obj._cfg).replace(
#                 "ConfigModel(",
#                 obj.__class__.__name__ + "(peer='" + obj.attached_to() + "', ",
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


def __pyaml_repr__(obj):
    """
    Returns a string representation of a pyaml object
    """

    attrs = {}

    # Instance attributes
    for k, v in obj.__dict__.items():
        # Exclude private attributes
        if not k.startswith("_"):
            attrs[k] = v

    # Properties
    for name, attr in vars(type(obj)).items():
        if isinstance(attr, property):
            try:
                attrs[name] = getattr(obj, name)
            except Exception as e:
                attrs[name] = f"<error: {e}>"

    parts = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
    return f"{obj.__class__.__name__}({parts})"


# class ElementConfigModel(BaseModel):
#     """
#     Base class for element configuration.

#     Parameters
#     ----------
#     name : str
#         The name of the PyAML element.
#     description : str, optional
#         Description of the element.
#     lattice_names : str or None, optional
#         The name(s) of the associated element(s) in the lattice. By default,
#         the PyAML element name is used. lattice_name accept the following
#         syntax:
#         - list(name,[name]) : Element names
#         - [name]@idx[,idx] : Element indices in the subset formed by name.
#         - [name]#start_idx..end_idx : Element range in the subset formed by name.
#         In the above syntax, if the name is not specficied, the whole set
#         of lattice element is used for indexing.
#     """

#     model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

#     name: str
#     description: str | None = None
#     lattice_names: str | None = None


@add_schema
class Element(object):
    """
    Class providing access to one element of a physical or simulated lattice

    Attributes:
      name: str
        The unique name identifying the element in the configuration file
    """

    def __init__(
        self,
        name: str,
        lattice_names: str | None = None,
        description: str | None = None,
    ):
        self._name: str = name

        # If no lattice names are given put it to the name of the element
        if lattice_names:
            self._lattice_names = lattice_names
        else:
            self._lattice_names = self._name

        self.description = description

        self._peer: "ElementHolder" = None  # Peer: ControlSystem, Simulator

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

    # TODO: implement lattice_names setter -> this requires validation of the forma

    def get_lattice_names(self) -> str:
        """
        Returns the name of associated lattice element(s)
        """
        warnings.warn(
            "get_lattice_names() is deprecated; use .lattice_names instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.lattice_names

    def get_description(self) -> str:
        """
        Returns the description of the element
        """
        warnings.warn(
            "get_description() is deprecated; use .description instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.description

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

    def attached_to(self) -> str:
        """
        Returns a string of which peer the element is attached to.
        """
        return "None" if self._peer is None else f"{self._peer.__class__.__name__}:{self._peer.name()}"

    def post_init(self):
        """
        Method triggered after all initialisations are done
        """
        pass

    def __repr__(self):
        return __pyaml_repr__(self)
