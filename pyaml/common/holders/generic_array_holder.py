"""Generic typed storage and lookup for arrays of accelerator elements."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar

from ..element import Element

if TYPE_CHECKING:
    from .element_holder import ElementHolder

T = TypeVar("T", bound=Element)
A = TypeVar("A")


class GenericArrayHolder(Generic[T, A]):
    """Provide typed access to named arrays of one element type.

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
        """Initialize an array holder with storage and lookup callbacks.

        Parameters
        ----------
        peer : 'ElementHolder'
            Parent element holder.
        array_store : dict[str, A]
            Mapping from array names to stored arrays.
        all_func : Callable[[], list[T]]
            Callback returning all elements.
        get_func : Callable[[str], T]
            Callback resolving an element by name.
        constructor : Callable[[str, list[T]], A]
            Callback constructing an array from a name and elements.
        what : str
            Human-readable array type used for lookup errors.
        """
        self._peer = peer
        self._array_store = array_store
        self._all_func = all_func
        self._get_func = get_func
        self._constructor = constructor
        self._what = what

    def get(self, name: str | None = None) -> A:
        """Return a named array or a transient array of all elements.

        Parameters
        ----------
        name : str or None, optional
            Array name. If ``None``, all available elements are returned.

        Returns
        -------
        A
            Requested named array or an array containing all elements.
        """
        if name is None:
            return self._constructor("", self._all_func())
        else:
            return self._peer._get(self._what, name, self._array_store)

    def add(self, arrayName: str, elementNames: list[str]):
        """Create and register a named array from element selectors.

        Parameters
        ----------
        arrayName : str
            Name under which to store the array.
        elementNames : list[str]
            Names of elements to include, in array order.

        Notes
        -----
        Selectors may use the lookup syntax supported by the parent
        :class:`~pyaml.common.holders.element_holder.ElementHolder`, including
        wildcard and exclusion patterns.
        """
        self._peer._fill_array(arrayName, elementNames, self._get_func, self._constructor, self._array_store)

    def __getitem__(self, key):
        """Return an element from the aggregate array by index.

        Parameters
        ----------
        key : int or slice
            Index or slice passed to the aggregate array.

        Returns
        -------
        object
            Element or sub-array selected by ``key``.
        """
        return self.get().__getitem__(key)
