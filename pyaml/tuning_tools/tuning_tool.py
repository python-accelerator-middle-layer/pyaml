import logging
from typing import Self

from ..common.element import Element
from ..common.element_holder import ElementHolder

logger = logging.getLogger(__name__)


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
        obj = self.__class__(self._cfg)
        obj._peer = peer
        return obj
