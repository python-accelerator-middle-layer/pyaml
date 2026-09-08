"""
Deferred construction of control-system-specific elements.

An :class:`UnboundElement` stores a class, validated configuration, and the
control modes in which it is available until an :class:`ElementHolder` is
known and the concrete element can be instantiated.
"""

from pydantic import BaseModel

from ..common.element import Element
from ..common.exception import PyAMLConfigException


class UnboundElement(Element):
    """
    Store configuration for an element instantiated when a holder is filled.

    Parameters
    ----------
    element_class : type
        Concrete element class to instantiate.
    module_name : str
        Module path used to identify the element in error messages.
    modes : list of str
        Control-system modes in which the element should be created.
    config : pydantic.BaseModel
        Validated configuration passed to the element constructor.

    Methods
    -------
    instantiate(holder)
        Instantiate the element represented by this UnboundElement.
    """

    def __init__(self, element_class, module_name: str, modes: list[str], config: BaseModel):
        """
        Initialize a deferred element configuration.
        """
        super().__init__(config.name)
        self._class = element_class
        self._module_name = module_name
        self._control_modes = modes
        self._config = config

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return "%s(name='%s', class_name='%s', module_name=%s)" % (
            self.__class__.__name__,
            self.get_name(),
            self._class.__name__,
            self._module_name,
        )

    def instantiate(self, holder) -> Element:
        """
        Instantiate the element represented by this UnboundElement.

        The element is constructed using the stored configuration and
        attached to the given ElementHolder. The returned element is
        linked back to the holder through its ``_peer`` attribute.

        Parameters
        ----------
        holder : ElementHolder
            Holder that owns the instantiated element.

        Returns
        -------
        Element
            Instantiated element attached to the given holder.

        Raises
        ------
        PyAMLConfigException
            If the element cannot be instantiated or if the resulting
            object is not a subclass of Element.
        """

        cls = self._class

        try:
            obj = cls(holder, self._config)
        except Exception as exc:
            raise PyAMLConfigException(f"{exc} when creating '{self._module_name}.{cls.__name__}'") from exc

        if not isinstance(obj, Element):
            raise PyAMLConfigException(f"'{self._module_name}.{cls.__name__}' is not a subclass of Element")

        obj._peer = holder
        return obj
