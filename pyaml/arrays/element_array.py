import fnmatch
import importlib
from typing import Sequence

import numpy as np

from ..bpm.bpm import BPM
from ..common.element import Element
from ..common.exception import PyAMLException
from ..magnet.cfm_magnet import CombinedFunctionMagnet
from ..magnet.magnet import Magnet
from ..magnet.serialized_magnet import SerializedMagnets


class ElementArray(list[Element]):
    """
    Class that implements access to an element array

    Parameters
    ----------
    array_name : str
        Array name
    elements : list[Element]
        Element list, all elements must be attached to the same instance of
        either a Simulator or a ControlSystem.
    use_aggregator : bool
        Use aggregator to increase performance by using paralell
        access to underlying devices.

    Example
    -------

    An array can be retrieved from the configuration as in the following example::

        .. code-block:: python

        >>> sr = Accelerator.load("acc.yaml")
        >>> elements = sr.design.get_elements("QuadForTune")

    """

    def __init__(self, array_name: str, elements: list[Element], use_aggregator=True):
        super().__init__(i for i in elements)
        self.__name = array_name
        self.__peer = None
        self.__use_aggregator = use_aggregator
        if len(elements) > 0:
            self.__peer = self[0]._peer if len(self) > 0 else None
            if self.__peer is None or any([m._peer != self.__peer for m in self]):
                raise PyAMLException(
                    f"{self.__class__.__name__} {self.get_name()}: "
                    "All elements must be attached to the same instance "
                    "of either a Simulator or a ControlSystem"
                )

    def get_peer(self):
        """
        Returns the peer (Simulator or ControlSystem) of an element list
        """
        return self.__peer

    def get_name(self) -> str:
        """
        Returns the array name
        """
        return self.__name

    def names(self) -> list[str]:
        """
        Returns the element names
        """
        return [e.get_name() for e in self]

    def __create_array(self, array_name: str, element_type: type, elements: list):
        if element_type is None:
            element_type = Element

        if issubclass(element_type, Magnet):
            m = importlib.import_module("pyaml.arrays.magnet_array")
            array_class = getattr(m, "MagnetArray", None)
            return array_class(array_name, elements, self.__use_aggregator)
        elif issubclass(element_type, BPM):
            m = importlib.import_module("pyaml.arrays.bpm_array")
            array_class = getattr(m, "BPMArray", None)
            return array_class(array_name, elements, self.__use_aggregator)
        elif issubclass(element_type, CombinedFunctionMagnet):
            m = importlib.import_module("pyaml.arrays.cfm_magnet_array")
            array_class = getattr(m, "CombinedFunctionMagnetArray", None)
            return array_class(array_name, elements, self.__use_aggregator)
        elif issubclass(element_type, SerializedMagnets):
            m = importlib.import_module("pyaml.arrays.serialized_magnet_array")
            array_class = getattr(m, "SerializedMagnetsArray", None)
            return array_class(array_name, elements, self.__use_aggregator)
        elif issubclass(element_type, Element):
            return ElementArray(array_name, elements, self.__use_aggregator)
        else:
            raise PyAMLException(
                f"Unsupported sliced array for type {str(element_type)}"
            )

    def __eval_field(self, attribute_name: str, element: Element) -> str:
        function_name = "get_" + attribute_name
        func = getattr(element, function_name, None)
        return func() if func is not None else ""

    def __ensure_compatible_operand(self, other: object) -> "ElementArray":
        """Validate the operand used for set-like operations between arrays."""
        if not isinstance(other, ElementArray):
            raise TypeError(
                f"Unsupported operand type(s) for set operation: "
                f"'{type(self).__name__}' and '{type(other).__name__}'"
            )

        if len(self) > 0 and len(other) > 0:
            if self.get_peer() is not None and other.get_peer() is not None:
                if self.get_peer() != other.get_peer():
                    raise PyAMLException(
                        f"{self.__class__.__name__}: cannot operate on arrays "
                        "attached to different peers"
                    )
        return other

    def __auto_array(self, elements: list[Element]):
        """Create the most specific array type for the given element list.

        The target element type is the most specific common base class (nearest common
        ancestor) of all elements. This supports heterogeneous subclasses (e.g.,
        several Magnet subclasses) while still returning a MagnetArray when
        appropriate.
        """
        if len(elements) == 0:
            return []

        import inspect

        def mro_as_list(cls: type) -> list[type]:
            # inspect.getmro returns (cls, ..., object)
            return list(inspect.getmro(cls))

        # Start from the first element MRO as reference order (most specific first).
        common: list[type] = mro_as_list(type(elements[0]))

        # Intersect while preserving MRO order from the first element.
        for e in elements[1:]:
            mro_set = set(mro_as_list(type(e)))
            common = [c for c in common if c in mro_set]
            if not common:
                break

        # Pick the first suitable common base within the Element hierarchy.
        chosen: type = Element
        for c in common:
            if c is object:
                continue
            if issubclass(c, Element):
                chosen = c
                break

        return self.__create_array("", chosen, elements)

    def __is_bool_mask(self, other: object) -> bool:
        """Return True if 'other' looks like a boolean mask (list or numpy array)."""
        # --- numpy boolean array ---
        try:
            if isinstance(other, np.ndarray) and other.dtype == bool:
                return True
        except Exception:
            pass

        # --- python sequence of bools (but not a string/bytes) ---
        if isinstance(other, Sequence) and not isinstance(
            other, (str, bytes, bytearray)
        ):
            # Avoid treating ElementArray as a mask
            if isinstance(other, ElementArray):
                return False
            # Accept only actual bool-like values
            try:
                return all(isinstance(v, bool) for v in other)
            except TypeError:
                return False

        return False

    def __and__(self, other: object):
        """
        Intersection or boolean mask filtering.

        This operator has two distinct behaviors depending on the type of
        ``other``.

        1) Array intersection
           If ``other`` is an ElementArray, the result contains elements
           whose names are present in both arrays.

           Example
           -------
           .. code-block:: python

           >>> cell1 = sr.live.get_elements("C01")
           >>> sexts = sr.live.get_magnets("SEXT")
           >>> cell1_sext = cell1 & sexts

        2) Boolean mask filtering
           If ``other`` is a boolean mask (list[bool] or numpy.ndarray of bool),
           elements are kept where the mask is True.

           Example
           -------
           .. code-block:: python

           >>> mask = cell1.mask_by_type(Magnet)
           >>> magnets = cell1 & mask

        Returns
        -------
        ElementArray or specialized array
            The result is automatically typed according to the most specific
            common base class of the remaining elements.
        """
        # --- mask filtering ---
        if self.__is_bool_mask(other):
            mask = list(other)  # works for list/tuple and numpy arrays
            if len(mask) != len(self):
                raise ValueError(
                    f"{self.__class__.__name__}: mask length ({len(mask)}) "
                    f"does not match array length ({len(self)})"
                )
            res = [e for e, keep in zip(self, mask, strict=True) if bool(keep)]
            return self.__auto_array(res)

        # --- array intersection ---
        other_arr = self.__ensure_compatible_operand(other)
        other_names = {e.get_name() for e in other_arr}
        res = [e for e in self if e.get_name() in other_names]
        return self.__auto_array(res)

    def __rand__(self, other: object):
        # Support "array on the right" for array operands; for masks, we don't enforce
        # commutativity.
        if isinstance(other, ElementArray):
            return other.__and__(self)
        return NotImplemented

    def __sub__(self, other: object):
        """
        Difference or boolean mask removal.

        This operator has two behaviors depending on the type of ``other``.

        1) Array difference
           If ``other`` is an ElementArray, the result contains elements
           whose names are present in ``self`` but not in ``other``.

           Example
           -------
           .. code-block:: python

           >>> hvcorr = sr.live.get_magnets("HVCORR")
           >>> hcorr = sr.live.get_magnets("HCORR")
           >>> vcorr_only = hvcorr - hcorr

        2) Boolean mask removal
           If ``other`` is a boolean mask (list[bool] or numpy.ndarray of bool),
           elements are removed where the mask is True.
           This is the inverse of ``& mask``.

           Example
           -------
           .. code-block:: python

           >>> mask = cell1.mask_by_type(Magnet)
           >>> non_magnets = cell1 - mask

        Returns
        -------
        ElementArray or specialized array
            The result is automatically typed according to the most specific
            common base class of the remaining elements.
        """
        # --- mask removal ---
        if self.__is_bool_mask(other):
            mask = list(other)
            if len(mask) != len(self):
                raise ValueError(
                    f"{self.__class__.__name__}: mask length ({len(mask)}) "
                    f"does not match array length ({len(self)})"
                )
            res = [e for e, remove in zip(self, mask, strict=True) if not bool(remove)]
            return self.__auto_array(res)

        # --- array difference ---
        other_arr = self.__ensure_compatible_operand(other)
        other_names = {e.get_name() for e in other_arr}
        res = [e for e in self if e.get_name() not in other_names]
        return self.__auto_array(res)

    def __or__(self, other: object):
        """
        Union between two ElementArray instances.

        Elements are combined using their names as identity.
        Order is stable: elements from ``self`` first, followed by
        elements from ``other`` that are not already present.

        Example
        -------
        .. code-block:: python

        >>> hcorr = sr.live.get_magnets("HCORR")
        >>> vcorr = sr.live.get_magnets("VCORR")
        >>> all_corr = hcorr | vcorr

        Returns
        -------
        ElementArray or specialized array
            The result is automatically typed according to the most specific
            common base class of the combined elements.
        """
        other_arr = self.__ensure_compatible_operand(other)

        seen: set[str] = set()
        res: list[Element] = []

        for e in self:
            name = e.get_name()
            if name not in seen:
                res.append(e)
                seen.add(name)

        for e in other_arr:
            name = e.get_name()
            if name not in seen:
                res.append(e)
                seen.add(name)

        return self.__auto_array(res)

    def __ror__(self, other: object):
        if isinstance(other, ElementArray):
            return other.__or__(self)
        return NotImplemented

    def __add__(self, other: object):
        """
        Alias for the union operator ``|``.

        Example
        -------
        .. code-block:: python

        >>> all_corr = hcorr + vcorr
        """
        return self.__or__(other)

    def __radd__(self, other: object):
        if isinstance(other, ElementArray):
            return other.__add__(self)
        return NotImplemented

    def mask_by_type(self, element_type: type) -> list[bool]:
        """Return a boolean mask indicating which elements are instances of the given
        type.

        Parameters
        ----------
        element_type : type
            The class to test against (e.g., Magnet).

        Returns
        -------
        list[bool]
            A list of booleans where True indicates the element is an instance
            of the given type (including subclasses).
        """
        if not isinstance(element_type, type):
            raise TypeError(f"{self.__class__.__name__}: element_type must be a type")

        return [isinstance(e, element_type) for e in self]

    def of_type(self, element_type: type):
        """Return a new array containing only elements of the given type.

        The resulting array is automatically typed according to the most
        specific common base class of the filtered elements.

        Parameters
        ----------
        element_type : type
            The class to filter by (e.g., Magnet).

        Returns
        -------
        ElementArray or specialized array
            An auto-typed array containing only matching elements.
            Returns [] if no elements match.
        """
        if not isinstance(element_type, type):
            raise TypeError(f"{self.__class__.__name__}: element_type must be a type")

        filtered = [e for e in self if isinstance(e, element_type)]
        return self.__auto_array(filtered)

    def exclude_type(self, element_type):
        mask = self.mask_by_type(element_type)
        return self - mask

    def __getitem__(self, key):
        if isinstance(key, slice):
            # Slicing
            element_type = None
            r = []
            for i in range(*key.indices(len(self))):
                if element_type is None:
                    element_type = type(self[i])
                elif not isinstance(self[i], element_type):
                    element_type = Element  # Fall back to element
                r.append(self[i])
            return self.__create_array("", element_type, r)

        elif isinstance(key, str):
            fields = key.split(":")

            if len(fields) <= 1:
                # Selection by name
                element_type = None
                r = []
                for e in self:
                    if fnmatch.fnmatch(e.get_name(), key):
                        if element_type is None:
                            element_type = type(e)
                        elif not isinstance(e, element_type):
                            element_type = Element  # Fall back to element
                        r.append(e)
            else:
                # Selection by fields
                element_type = None
                r = []
                for e in self:
                    txt = self.__eval_field(fields[0], e)
                    if fnmatch.fnmatch(txt, fields[1]):
                        if element_type is None:
                            element_type = type(e)
                        elif not isinstance(e, element_type):
                            element_type = Element  # Fall back to element
                        r.append(e)

            return self.__create_array("", element_type, r)

        else:
            # Default to super selection
            return super().__getitem__(key)
