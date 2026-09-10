"""Base classes for configured accelerator and lattice elements."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from .exception import PyAMLException

if TYPE_CHECKING:
    from .holders.element_holder import ElementHolder


def __pyaml_repr__(obj, exclude: list[str] | None = None):
    """
    Build a representation from configuration fields and public properties.

    Parameters
    ----------
    obj : object
        Object to represent.
    exclude : list[str] | None
        Attribute or property names to exclude from the output.
    """

    if exclude is None:
        exclude = []

    cls_name = obj.__class__.__name__

    # Keep the old behavior when _cfg exists
    cfg = getattr(obj, "_cfg", None)
    if cfg is not None:
        if isinstance(obj, Element):
            return repr(cfg).replace(
                "ConfigModel(",
                f"{cls_name}(peer={obj.attached_to()!r}, ",
                1,
            )
        return repr(cfg).replace("ConfigModel", cls_name, 1)

    # Generic fallback when there is no _cfg
    attrs = {}

    # Instance attributes
    for k, v in obj.__dict__.items():
        # Exclude private attributes and excluded
        if not k.startswith("_") and k not in exclude:
            attrs[k] = v

    # Properties
    for name, attr in vars(type(obj)).items():
        if isinstance(attr, property) and name not in exclude:
            try:
                attrs[name] = getattr(obj, name)
            except Exception as e:
                attrs[name] = f"<error: {e}>"

    if isinstance(obj, Element) and "name" not in attrs and "name" not in exclude:
        try:
            attrs["name"] = obj.get_name()
        except Exception as e:
            attrs["name"] = f"<error: {e}>"

    parts = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
    return f"{cls_name}({parts})" if parts else cls_name


class ElementConfigModel(BaseModel):
    """
    Base class for element configuration.

    Parameters
    ----------
    name : str
        The name of the PyAML element.
    description : str, optional
        Human-readable description of the element.
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


class Element:
    """
    Base class for an element in a physical or simulated lattice.

    Parameters
    ----------
    name : str
        Unique element name.
    lattice_names : str or None, optional
        Lattice element selector associated with this element. Defaults to
        ``name`` when omitted.
    description : str or None, optional
        Human-readable element description.

    Attributes
    ----------
    name
        Return the element name.
    lattice_names
        Return the lattice selector associated with the element.
    description
        Return the element description, if one is configured.
    peer
        Return the simulator or control system attached to the element.

    Methods
    -------
    get_name()
        Return the element name.
    get_lattice_names()
        Return the lattice selector associated with the element.
    get_description()
        Return the element description, if available.
    set_energy(E)
        Set the beam energy used by this element, if supported.
    set_mcf(alphac)
        Set the momentum compaction factor, if supported.
    set_harmonic(h)
        Set the RF harmonic number, if supported.
    check_peer()
        Raise an error if the element is not attached to a peer.
    attached_to()
        Return a human-readable description of the attached peer.
    post_init()
        Perform post-construction initialization after attachment.
    """

    def __init__(
        self,
        name: str,
        lattice_names: str | None = None,
        description: str | None = None,
    ):
        """
        Initialize an element and its optional lattice association.
        """
        self._name = name
        self._lattice_names = lattice_names
        self._description = description
        self._peer: ElementHolder | None = None

    def _cfg_value(self, attr: str, fallback: Any) -> Any:
        """
        Return a configured attribute, falling back to the base value.

        Parameters
        ----------
        attr : str
            Configuration attribute name.
        fallback : object
            Value returned when no configured value is available.
        """
        cfg = getattr(self, "_cfg", None)
        if cfg is not None:
            value = getattr(cfg, attr, None)
            if value is not None:
                return value
        return fallback

    @property
    def name(self) -> str:
        """Return the element name."""
        return self._cfg_value("name", self._name)

    @property
    def lattice_names(self) -> str:
        """Return the lattice selector associated with the element."""
        cfg = getattr(self, "_cfg", None)

        if cfg is not None and cfg.lattice_names is not None:
            return cfg.lattice_names

        if self._lattice_names is not None:
            return self._lattice_names

        return self.name

    @property
    def description(self) -> str | None:
        """Return the element description, if one is configured."""
        return self._cfg_value("description", self._description)

    def get_name(self) -> str:
        """Return the element name."""
        return self.name

    def get_lattice_names(self) -> str | None:
        """Return the lattice selector associated with the element."""
        return self.lattice_names

    def get_description(self) -> str | None:
        """Return the element description, if available."""
        return self.description

    def set_energy(self, E: float):
        """
        Set the beam energy used by this element, if supported.

        Parameters
        ----------
        E : float
            Beam energy.
        """
        pass

    def set_mcf(self, alphac: float):
        """
        Set the momentum compaction factor, if supported.

        Parameters
        ----------
        alphac : float
            Momentum compaction factor.
        """
        pass

    def set_harmonic(self, h: int):
        """
        Set the RF harmonic number, if supported.

        Parameters
        ----------
        h : int
            Number of RF buckets per revolution.
        """
        pass

    def check_peer(self):
        """
        Raise an error if the element is not attached to a peer.

        Raises
        ------
        PyAMLException
            If the element is not attached to a simulator or control system.
        """
        if self._peer is None:
            raise PyAMLException(f"{str(self.name)} is not attachedto a control system or the a simulator")

    @property
    def peer(self) -> "ElementHolder":
        """Return the simulator or control system attached to the element."""
        return self._peer

    def attached_to(self) -> str:
        """
        Return a human-readable description of the attached peer.

        Returns
        -------
        str
            Peer type and name, or ``"None"`` when unattached.
        """
        return "None" if self._peer is None else f"{self._peer.__class__.__name__}:{self._peer.name()}"

    def _fill_device(self, holder: "ElementHolder"):
        """
        Add this element to a holder (Simultor or ControlSystem)
        """
        raise PyAMLException(f"__fill_device() is not implemented for {self.__class__.__name__}")

    def post_init(self):
        """
        Perform post-construction initialization after attachment.

        Base elements do not require additional initialization.
        """
        pass

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return __pyaml_repr__(self)
