from ..common.element_holder import ElementHolder
from .array import ArrayConfig, ArrayConfigModel

# Define the main class name for this module
PYAMLCLASS = "Element"


class ConfigModel(ArrayConfigModel): ...


class Element(ArrayConfig):
    """
    Element array confirguration

    Example
    -------

    An element array configuration can also be created by code using
    the following example::

        from pyaml.arrays.element import Element,ConfigModel as ElementArrayConfigModel
        elemArray = Element(
                      ElementArrayConfigModel(name="MyArray", elements=["elt1","elt2"])
                    )


    """

    def __init__(self, cfg: ArrayConfigModel):
        super().__init__(cfg)

    def fill_array(self, holder: ElementHolder):
        holder.fill_element_array(self._cfg.name, self._cfg.elements)
