"""Generic typed storage and lookup for arrays of accelerator elements."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar

from ..element import Element, __pyaml_repr__

if TYPE_CHECKING:
    from .element_holder import ElementHolder

T = TypeVar("T", bound=Element)
A = TypeVar("A")


class GenericArrayHolder(Generic[T, A]):
    """
    Provide typed access to named arrays of one element type.

    Concrete holders (:class:`.MagnetsHolder`, :class:`.SerializedMagnetsHolder`,
    :class:`.CombinedFunctionMagnetsHolder`, ...) subclass this with the
    element type ``T`` and the array type ``A`` they handle, so callers keep
    full static typing on :meth:`get`, :meth:`add` and :meth:`__getitem__`.

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

    Methods
    -------
    get(name=None)
        Return a named array or a transient array of all elements.
    add(arrayName, elementNames)
        Create and register a named array from element selectors.

    Notes
    -----
    A configured array is also reachable as an attribute when its name is a
    valid Python identifier, e.g. ``holder.QuadForTune`` is equivalent to
    ``holder.get("QuadForTune")``. Array names appear in ``dir(holder)`` so
    interactive completion (IPython, Jupyter) discovers them.
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
        """
        Initialize an array holder with storage and lookup callbacks.
        """
        self._peer = peer
        self._array_store = array_store
        self._all_func = all_func
        self._get_func = get_func
        self._constructor = constructor
        self._what = what

    def get(self, name: str | None = None) -> A:
        """
        Return a named array or a transient array of all elements.

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
        """
        Create and register a named array from element selectors.

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
        """
        Select from the aggregate array of every individual element.

        Delegates to :meth:`ElementArray.__getitem__
        <pyaml.arrays.element_array.ElementArray.__getitem__>` on ``self.get()``
        (the array of every individual element of this type), so ``key``
        matches against **individual element names**, not against the
        registered array/family names that :meth:`get` searches. These are
        deliberately two different, non-overlapping namespaces: ``get(name)``
        looks up a configured family (e.g. ``"QForTune"``), while ``[key]``
        looks up the elements themselves (e.g. ``"QF1A-C01"`` or ``"QF1*"``).

        Parameters
        ----------
        key : int, slice, str, list[str] or tuple[str, ...]
            Index or slice into the aggregate array, an individual element's
            exact name, an fnmatch wildcard or ``re:`` regular expression
            over element names, or a list/tuple of such patterns.

        Returns
        -------
        object
            Element or sub-array selected by ``key``.

        Raises
        ------
        PyAMLException
            If ``key`` is an exact literal element name (or a literal entry
            within a list or tuple) that matches no individual element, or a
            ``re:`` pattern is not a valid regular expression.

        Examples
        --------
        >>> family = sr.live.magnets.get("QForTune")  # array-name namespace
        >>> one_magnet = sr.live.magnets["QF1A-C01"]  # element-name namespace
        >>> some_magnets = sr.live.magnets["QF1*"]  # element-name namespace
        """
        return self.get().__getitem__(key)

    def __getattr__(self, name: str) -> A:
        """
        Return a configured array through attribute access.

        Only called when normal attribute lookup fails, so it never shadows
        :meth:`get`, :meth:`add`, or any other existing attribute.

        Parameters
        ----------
        name : str
            Configured array name. Must be a valid Python identifier.

        Returns
        -------
        A
            The array registered under ``name``.

        Raises
        ------
        AttributeError
            If ``name`` starts with an underscore, is not a valid Python
            identifier, or does not match a configured array.

        Examples
        --------
        >>> quad_family = sr.live.magnets.get("QuadForTune")
        >>> same_quad_family = sr.live.magnets.QuadForTune
        """
        if name.startswith("_") or not name.isidentifier() or name not in self._array_store:
            raise AttributeError(f"'{type(self).__name__}' object has no array named '{name}'")
        return self._array_store[name]

    def __dir__(self) -> list[str]:
        """
        List attributes, including configured array names.

        Returns
        -------
        list of str
            Default attributes plus configured array names that are valid
            Python identifiers, for interactive completion (IPython, Jupyter).
        """
        return sorted(set(super().__dir__()) | {name for name in self._array_store if name.isidentifier()})

    def __repr__(self):
        return __pyaml_repr__(self)
