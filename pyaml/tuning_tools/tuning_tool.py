import copy
from typing import Self

from ..common.element import Element
from ..common.holders.element_holder import ElementHolder


class TuningTool(Element):
    """
    Base class for tuning tool such as tune adjustment or other tuning tools.
    """

    def __init__(self, name):
        super().__init__(name)

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Create a new reference to attach this tuning tool object to a simulator
        or a control system.
        """
        if hasattr(self, "_cfg"):
            obj = self.__class__(self._cfg)
        else:
            obj = copy.copy(self)
            obj._after_attach()
        obj._peer = peer
        return obj

    def fill_device(self, holder: "ElementHolder") -> None:
        holder.fill_tool(self)

    def _after_attach(self) -> None:
        """Hook for subclasses to rebind internal references after attach."""
        pass
