"""Generic typed storage and lookup for accelerator elements."""

from typing import TYPE_CHECKING, Generic, TypeVar

from ..element import Element, __pyaml_repr__

if TYPE_CHECKING:
    from .element_holder import ElementHolder

T = TypeVar("T", bound=Element)


class GenericElementHolder(Generic[T]):
    """
    Provide typed name-based access to one category of elements.

    Concrete holders (:class:`.MagnetHolder`, :class:`.SerializedMagnetHolder`,
    :class:`.CombinedFunctionMagnetHolder`, ...) subclass this with the
    element type they handle, so callers keep full static typing on
    :meth:`all`, :meth:`get` and :meth:`add`.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder.
    store : dict[str, T]
        Mapping from element names to elements.
    what : str
        Human-readable element type used for lookup errors.

    Methods
    -------
    all()
        Return all stored elements in insertion order.
    get(name)
        Return the element with the requested name.
    add(m)
        Add an element to the holder's name-indexed store.
    """

    def __init__(self, peer: "ElementHolder", store: dict[str, T], what: str):
        """
        Initialize a holder backed by an element store.
        """
        self._peer = peer
        self._store = store
        self._what = what

    def all(self) -> list[T]:
        """
        Return all stored elements in insertion order.

        Returns
        -------
        list of T
            Elements currently registered in this category.
        """
        return [value for key, value in self._store.items()]

    def get(self, name: str) -> T:
        """
        Return the element with the requested name.

        Parameters
        ----------
        name : str
            Element name.

        Returns
        -------
        T
            Element registered under ``name``.
        """
        return self._peer._get(self._what, name, self._store)

    def add(self, m: T):
        """
        Add an element to the holder's name-indexed store.

        Parameters
        ----------
        m : T
            Element to add.

        Returns
        -------
        None
            This method updates the holder in place.
        """
        self._peer._add(self._store, m)

    def __repr__(self):
        return __pyaml_repr__(self)
