"""Generic typed storage and lookup for one family of accelerator elements and its arrays."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar

from ...arrays.element_array import ElementArray
from ..element import Element, __pyaml_repr__
from ..name_matching import is_wildcard, resolve_names

if TYPE_CHECKING:
    from .element_holder import ElementHolder

T = TypeVar("T", bound=Element)
A = TypeVar("A")


class GenericHolder(Generic[T, A]):
    """
    Provide typed access to one family of elements and to its configured arrays.

    Concrete holders (:class:`.MagnetHolder`, :class:`.CombinedFunctionMagnetHolder`,
    :class:`.SerializedMagnetHolder`, :class:`.BPMHolder`) subclass this with the
    element type ``T`` and the array type ``A`` they handle, so callers keep full
    static typing.

    The method decides what comes back. :meth:`get` always returns one element,
    :meth:`get_array` and attribute access always return an array. Element names
    and array names live in two separate namespaces, so they never clash.

    Parameters
    ----------
    peer : 'ElementHolder'
        Parent element holder.
    store : dict[str, T]
        Mapping from element names to elements.
    array_store : dict[str, A]
        Mapping from array names to configured arrays.
    array_cls : Callable[[str, list[T]], A]
        Array type, called with a name and a list of elements.
    what : str
        Human-readable element type used for lookup errors.
    resolver : Callable[[str], T], optional
        Callback resolving a name listed in a configured array. Defaults to
        :meth:`get`.
    members_func : Callable[[str], list[str] | None], optional
        Callback returning the names of the members of a group element (a
        serialized family), ``None`` for an element that is not a group. See
        :meth:`ElementHolder._fill_array
        <pyaml.common.holders.element_holder.ElementHolder._fill_array>`.

    Methods
    -------
    get(name)
        Return the element with the requested name.
    get_array(name=None)
        Return a configured array, or an array of every element of the family.
    add(element)
        Add an element to the holder.
    add_array(array_name, element_names)
        Create and register a configured array from element selectors.

    Notes
    -----
    A configured array is also reachable as an attribute when its name is a
    valid Python identifier, e.g. ``holder.QuadForTune`` is equivalent to
    ``holder.get_array("QuadForTune")``. Array names appear in ``dir(holder)``
    so interactive completion (IPython, Jupyter) discovers them.

    Examples
    --------
    >>> quad = sr.live.magnet.get("QF1A-C01")  # one element
    >>> quad_family = sr.live.magnet.get_array("QuadForTune")  # configured array
    >>> same_quad_family = sr.live.magnet.QuadForTune
    >>> all_magnets = sr.live.magnet.get_array()
    >>> same_quad = sr.live.magnet["QF1A-C01"]  # literal name: one element
    >>> some_quads = sr.live.magnet["QF1*"]  # pattern: typed array
    """

    def __init__(
        self,
        peer: "ElementHolder",
        store: dict[str, T],
        array_store: dict[str, A],
        array_cls: Callable[[str, list[T]], A],
        what: str,
        resolver: Callable[[str], T] | None = None,
        members_func: Callable[[str], list[str] | None] | None = None,
    ):
        """
        Initialize a holder backed by an element store and an array store.
        """
        self._peer = peer
        self._store = store
        self._array_store = array_store
        self._array_cls = array_cls
        self._what = what
        self._resolver = resolver if resolver is not None else self.get
        self._members_func = members_func

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

        Raises
        ------
        PyAMLException
            If no element of this family is registered under ``name``.
        """
        return self._peer._get(self._what, name, self._store)

    def get_array(self, name: str | None = None) -> A:
        """
        Return a configured array, or an array of every element of the family.

        Parameters
        ----------
        name : str or None, optional
            Configured array name. If ``None``, a new unnamed array holding
            every element of the family, in registration order, is returned.

        Returns
        -------
        A
            Requested configured array, or an array of every element.

        Raises
        ------
        PyAMLException
            If ``name`` is given and no array of this family is registered
            under it.
        """
        if name is None:
            return self._array_cls("", list(self._store.values()))
        return self._peer._get(f"{self._what} array", name, self._array_store)

    def __getitem__(self, key: int | slice | str | list[str] | tuple[str, ...]) -> "T | ElementArray":
        """
        Return an element, or a selection typed as the most specific compatible array.

        Parameters
        ----------
        key : int, slice, str, list[str] or tuple[str, ...]
            An exact literal name returns the stored element. An fnmatch
            wildcard (``*``, ``?`` or ``[``), a ``re:``-prefixed regular
            expression, a ``~``-prefixed exclusion, or a list/tuple of such
            patterns returns the most specific compatible array of matches
            (possibly empty), like :meth:`.ElementHolder.__getitem__`. An
            index or a slice applies to :meth:`get_array`.

        Returns
        -------
        T or ElementArray
            The stored element for an exact literal name or an index,
            otherwise a typed array.

        Raises
        ------
        PyAMLException
            If an exact literal name, or a literal entry within a list or
            tuple, does not match any element in this holder, or a ``re:``
            pattern is not a valid regular expression.
        IndexError
            If the index is out of bounds.
        """
        if isinstance(key, (int, slice)):
            return self.get_array()[key]
        if isinstance(key, str) and not key.startswith(("re:", "~")) and not is_wildcard(key):
            return self.get(key)
        matched = set(resolve_names(self._store.keys(), key, what=self._what))
        elements = [v for n, v in self._store.items() if n in matched]
        return ElementArray("", elements)._typed_array(elements)

    def add(self, element: T):
        """
        Add an element to the holder.

        Parameters
        ----------
        element : T
            Element to add, keyed by its own name.
        """
        self._peer._add(self._store, element)

    def add_array(self, array_name: str, element_names: list[str]):
        """
        Create and register a configured array from element selectors.

        Parameters
        ----------
        array_name : str
            Name under which to store the array.
        element_names : list[str]
            Names of elements to include, in array order.

        Notes
        -----
        Selectors may use the lookup syntax supported by the parent
        :class:`~pyaml.common.holders.element_holder.ElementHolder`, including
        wildcard and exclusion patterns.
        """
        self._peer._fill_array(
            array_name, element_names, self._resolver, self._array_cls, self._array_store, self._members_func
        )

    def __getattr__(self, name: str) -> A:
        """
        Return a configured array through attribute access.

        Only called when normal attribute lookup fails, so it never shadows
        :meth:`get`, :meth:`get_array`, or any other existing attribute.

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
