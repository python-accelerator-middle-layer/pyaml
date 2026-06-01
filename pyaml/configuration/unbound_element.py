from pydantic import BaseModel

from ..common.element import Element
from ..common.exception import PyAMLConfigException


class UnboundElement(Element):
    """
    Class that holds a configuration for an element created on the fly when ElementHolder is filled
    """

    def __init__(self, element_class, module_name: str, modes: list[str], config: BaseModel):
        """
        Construct an External element
        Parameters
        ----------
        element_class : class
            Element class
        module_name : str
            Element module
        control_modes: list[str]
            List of control modes to add the element to
        config: BaseModel
            Element configuration
        """
        super().__init__(config.name)
        self._class = element_class
        self._module_name = module_name
        self._control_modes = modes
        self._config = config

    def __repr__(self):
        return "%s(name='%s', class_name='%s', module_name=%s)" % (
            self.__class__.__name__,
            self.get_name(),
            self._class.__name__,
            self._module_name,
        )

    def instantiate(self, holder) -> Element:
        cls = self._class

        try:
            obj = cls(holder, self._config)
        except Exception as exc:
            raise PyAMLConfigException(f"{exc} when creating '{self._module_name}.{cls.__name__}'") from exc

        if not isinstance(obj, Element):
            raise PyAMLConfigException(f"'{self._module_name}.{cls.__name__}' is not a subclass of Element")

        obj._peer = holder
        return obj
