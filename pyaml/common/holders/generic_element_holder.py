from typing import TYPE_CHECKING, Generic, TypeVar

from ..element import Element, __pyaml_repr__

if TYPE_CHECKING:
    from .element_holder import ElementHolder

T = TypeVar("T", bound=Element)


class GenericElementHolder(Generic[T]):
    """
    Generic holder for a single kind of element (e.g. magnets, BPMs).

    Concrete holders (:class:`.MagnetHolder`, :class:`.SerializedMagnetHolder`,
    :class:`.CombinedFunctionMagnetHolder`, ...) subclass this with the
    element type they handle, so callers keep full static typing on
    :meth:`all`, :meth:`get` and :meth:`add`.
    """

    def __init__(self, peer: "ElementHolder", store: dict[str, T], what: str):
        self._peer = peer
        self._store = store
        self._what = what

    def all(self) -> list[T]:
        """
        Returns all elements as a list
        """
        return [value for key, value in self._store.items()]

    def get(self, name: str) -> T:
        """
        Returns the specified element

        Parameters
        ----------
        name : str
            Name of the element
        """
        return self._peer._get(self._what, name, self._store)

    def add(self, m: T):
        """
        Adds the specified element to the holder

        Parameters
        ----------
        m : T
           Element to be added
        """
        self._peer._add(self._store, m)

    def __repr__(self):
        return __pyaml_repr__(self)
