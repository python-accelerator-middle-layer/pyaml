"""
Base class for accelerator tuning tools.

The classes in this module provide the common lifecycle for tools that adjust
accelerator parameters, including attachment to a simulator or control system.
"""

import copy
from typing import Self

from ..common.element import Element
from ..common.holders.element_holder import ElementHolder


class TuningTool(Element):
    """
    Base class for tools that measure or adjust accelerator parameters.

    Tuning tools are configured independently and attached to an element holder
    before they access accelerator devices.

    Parameters
    ----------
    name : object
        Name of the tuning tool.

    Methods
    -------
    attach(peer)
        Return a copy of this tool bound to one control system or simulator.
    """

    def __init__(self, name):
        """
        Initialize a tuning tool.

        Parameters
        ----------
        name : object
            Name of the tuning tool.
        """
        super().__init__(name)

    def attach(self, peer: "ElementHolder") -> Self:
        """
        Return a copy attached to a simulator or control system.

        The configured tool remains reusable. Subclasses may override
        :meth:`_after_attach` to recreate handles that depend on the attached
        element holder.

        Parameters
        ----------
        peer : ElementHolder
            Element holder providing access to accelerator devices.

        Returns
        -------
        Self
            Attached copy of the tuning tool.
        """
        if hasattr(self, "_cfg"):
            obj = self.__class__(self._cfg)
        else:
            obj = copy.copy(self)
            obj._after_attach()
        obj._peer = peer
        return obj

    def _after_attach(self) -> None:
        """Hook for subclasses to rebind internal references after attach."""
        pass
