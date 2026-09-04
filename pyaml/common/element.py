from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from .exception import PyAMLException

if TYPE_CHECKING:
    from .holders.element_holder import ElementHolder


def __pyaml_repr__(obj, exclude: list[str] | None = None):
    """
    Returns a string representation of a pyaml object,
    including inherited properties and one level of nested objects.
    """
    if exclude is None:
        exclude = []

    cls_name = obj.__class__.__name__

    attrs = {}

    for name in dir(obj):
        # Skip private attributes and user-excluded names
        if name.startswith("_") or name in exclude:
            continue

        try:
            value = getattr(obj, name)

            # Skip methods/functions (we only want data)
            # This prevents: BPM(get_name=<bound method...>)
            if callable(value):
                continue

            if name == "peer":
                value = obj.attached_to() if isinstance(obj, Element) else value.__class__.__name__

            attrs[name] = value
        except Exception as e:
            attrs[name] = f"<error: {e}>"

    # Special handling for 'name' if it's an Element but not in attrs
    if isinstance(obj, Element) and "name" not in attrs and "name" not in exclude:
        try:
            attrs["name"] = obj.get_name()
        except Exception:
            pass

    # The !r flag ensures that if 'v' is another pyaml object,
    # its own __repr__ is called (providing the "one level below" effect).
    if not attrs:
        return cls_name
    parts = ", ".join(f"{k}={v!r}" for k, v in sorted(attrs.items())[:10])
    # Limit to 10 attributes to avoid overly long representations
    return f"{cls_name}({parts})"


class ElementConfigModel(BaseModel):
    """
    Base class for element configuration.

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

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    description: str | None = None
    lattice_names: str | None = None


class Element:
    """
    Class providing access to one element of a physical or simulated lattice
    """

    def __init__(
        self,
        name: str,
        lattice_names: str | None = None,
        description: str | None = None,
    ):
        self._name = name
        self._lattice_names = lattice_names
        self._description = description
        self._peer: ElementHolder | None = None

    def _cfg_value(self, attr: str, fallback: Any) -> Any:
        """
        Return an attribute from _cfg if available, otherwise fallback.
        """
        cfg = getattr(self, "_cfg", None)
        if cfg is not None:
            value = getattr(cfg, attr, None)
            if value is not None:
                return value
        return fallback

    @property
    def name(self) -> str:
        return self._cfg_value("name", self._name)

    @property
    def lattice_names(self) -> str:
        cfg = getattr(self, "_cfg", None)

        if cfg is not None and cfg.lattice_names is not None:
            return cfg.lattice_names

        if self._lattice_names is not None:
            return self._lattice_names

        return self.name

    @property
    def description(self) -> str | None:
        return self._cfg_value("description", self._description)

    def get_name(self) -> str:
        """
        Returns the name of the element
        """
        return self.name

    def get_lattice_names(self) -> str | None:
        return self.lattice_names

    def get_description(self) -> str | None:
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
            raise PyAMLException(f"{str(self.name)} is not attachedto a control system or the a simulator")

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
