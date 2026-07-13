from dataclasses import dataclass

import at

from pyaml.common.element import Element
from pyaml.lattice.lattice_elements_linker import (
    LatticeElementsLinker,
    LinkerConfigModel,
    LinkerIdentifier,
)

PYAMLCLASS = "PyAtAttributeElementsLinker"


@dataclass
class PyAtAttributeConfigModel(LinkerConfigModel):
    """Configuration model for ``PyAtAttributeElementsLinker``.

    Parameters
    ----------
    attribute_name : str
        Name of the PyAT element attribute used to identify matching
        lattice elements.
    """

    attribute_name: str


class PyAtAttributeIdentifier(LinkerIdentifier):
    """Identifier based on a PyAT element attribute.

    Parameters
    ----------
    attribute_name : str
        Name of the PyAT attribute used for matching.
    identifier
        Expected value of the attribute.
    """

    def __init__(self, attribute_name: str, identifier):
        self.attribute_name = attribute_name
        self.identifier = identifier

    def __repr__(self):
        return f"{self.attribute_name}={self.identifier}"


class PyAtAttributeElementsLinker(LatticeElementsLinker):
    """Link lattice elements using a specified PyAT element attribute.

    This linker associates PyAML elements with PyAT elements by comparing
    the value of a configurable PyAT attribute against the identifier
    extracted from the PyAML element.
    """

    def __init__(self, attribute_name: str):
        config_model = PyAtAttributeConfigModel(attribute_name)
        super().__init__(config_model)

    def get_element_identifier(self, element: Element) -> LinkerIdentifier:
        """
        Get the element identifier for the given element.

        Parameters
        ----------
        element : Element
            The element to get the identifier for

        Returns
        -------
        LinkerIdentifier
            The identifier for linking the element
        """
        return PyAtAttributeIdentifier(self.linker_config_model.attribute_name, element.get_name())

    def _test_at_element(self, identifier: PyAtAttributeIdentifier, element: at.Element) -> bool:
        attr_value = getattr(element, identifier.attribute_name, None)
        return attr_value == identifier.identifier
