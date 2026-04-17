from ..common.element import Element

class ExternalElement(Element):
    """
    Class that holds a configuration for an external element
    """

    def __init__(self, name: str, class_name:str, module_name:str, modes:list[str], config:dict):
        """
        Construct an External element
        Parameters
        ----------
        name : str
            Element name
        class_name : str
            Element class
        module_name : str
            Element module
        mode: list[str]
            List of control mode to add the element
        config: dict
            Element configuration
        """
        super().__init__(name)
        self._class_name = class_name
        self._module_name = module_name
        self._modes = modes
        self._config = config

    def __repr__(self):
        return "%s(name='%s', class_name='%s', module_name=%s)" % (
            self.__class__.__name__,
            self.get_name(),
            self._class_name,
            self._module_name
        )
