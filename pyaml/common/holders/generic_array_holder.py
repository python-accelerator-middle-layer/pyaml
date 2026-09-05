from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar

from ..element import Element, __pyaml_repr__

if TYPE_CHECKING:
    from .element_holder import ElementHolder

T = TypeVar("T", bound=Element)
A = TypeVar("A")


class GenericArrayHolder(Generic[T, A]):
    """
    Generic holder for arrays of elements (e.g. magnet arrays, BPM arrays).

    Concrete holders (:class:`.MagnetsHolder`, :class:`.SerializedMagnetsHolder`,
    :class:`.CombinedFunctionMagnetsHolder`, ...) subclass this with the
    element type ``T`` and the array type ``A`` they handle, so callers keep
    full static typing on :meth:`get`, :meth:`add` and :meth:`__getitem__`.
    """

    def __init__(
        self,
        peer: "ElementHolder",
        array_store: dict[str, A],
        all_func: Callable[[], list[T]],
        get_func: Callable[[str], T],
        constructor: Callable[[str, list[T]], A],
        what: str,
    ):
        self._peer = peer
        self._array_store = array_store
        self._all_func = all_func
        self._get_func = get_func
        self._constructor = constructor
        self._what = what

    def get(self, name: str | None = None) -> A:
        """
        Returns the specified array or all elements if no name specified

        Parameters
        ----------
        name : str
            Name of the array
        """
        if name is None:
            return self._constructor("", self._all_func())
        else:
            return self._peer._get(self._what, name, self._array_store)

    def add(self, arrayName: str, elementNames: list[str]):
        """
        Adds the specified array to the holder

        Parameters
        ----------
        arrayName : str
            Array name
        elementNames : list[str]
            List of element names
        """
        self._peer._fill_array(arrayName, elementNames, self._get_func, self._constructor, self._array_store)

    def __getitem__(self, key):
        return self.get().__getitem__(key)

    def __repr__(self):
        return __pyaml_repr__(self)
