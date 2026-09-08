"""
Link PyAML elements to Accelerator Toolbox elements by attributes.

This module compares a configured PyAT attribute with a PyAML element name to
identify the corresponding lattice element during simulator initialization.
"""

from dataclasses import dataclass

import at

from pyaml.common.element import Element
from pyaml.lattice.lattice_elements_linker import (
    LatticeElementsLinker,
    LinkerConfigModel,
    LinkerIdentifier,
)

from ..validation import DynamicValidation, register_schema

PYAMLCLASS = "PyAtAttributeElementsLinker"


@dataclass
class PyAtAttributeConfigModel(LinkerConfigModel):
    """
    Configuration model for ``PyAtAttributeElementsLinker``.

    Parameters
    ----------
    attribute_name : str
        Name of the PyAT element attribute used to identify matching
        lattice elements.
    """

    attribute_name: str


class PyAtAttributeIdentifier(LinkerIdentifier):
    """
    Identifier based on a PyAT element attribute.

    Parameters
    ----------
    attribute_name : str
        Name of the PyAT attribute used for matching.
    identifier
        Expected value of the attribute.
    """

    def __init__(self, attribute_name: str, identifier):
        """
        Create an attribute-based lattice-element identifier.

        The identifier is later compared with the value of ``attribute_name``
        on each PyAT element considered by the linker.

        Parameters
        ----------
        attribute_name : str
            Name of the PyAT attribute used for matching.
        identifier : object
            Expected value of the matching PyAT attribute.
        """
        self.attribute_name = attribute_name
        self.identifier = identifier

    def __repr__(self):
        """
        Implement the ``__repr__`` string.
        """
        return f"{self.attribute_name}={self.identifier}"


@register_schema
class PyAtAttributeElementsLinker(LatticeElementsLinker, DynamicValidation):
    """
    Link lattice elements using a specified PyAT element attribute.

    This linker associates PyAML elements with PyAT elements by comparing
    the value of a configurable PyAT attribute against the identifier
    extracted from the PyAML element.
    """

    def __init__(self, attribute_name: str):
        """
        Configure an attribute-based PyAT element linker.

        During simulator initialization, the linker compares this attribute's
        value on each PyAT element with the corresponding PyAML element name.

        Parameters
        ----------
        attribute_name : str
            Name of the PyAT attribute used to identify matching elements.
        """
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
        """
        Check whether a PyAT element matches a linker identifier.

        Parameters
        ----------
        identifier : PyAtAttributeIdentifier
            Attribute name and expected identifier to compare.
        element : at.Element
            PyAT lattice element being tested.

        Returns
        -------
        bool
            ``True`` if the attribute value matches; otherwise ``False``.
        """
        attr_value = getattr(element, identifier.attribute_name, None)
        return attr_value == identifier.identifier
