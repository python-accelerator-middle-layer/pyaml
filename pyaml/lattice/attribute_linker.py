import at
from pydantic import ConfigDict

from pyaml.common.element import Element
from pyaml.lattice.lattice_elements_linker import LinkerIdentifier, LinkerConfigModel, LatticeElementsLinker

PYAMLCLASS = "PyAtAttributeElementsLinker"


class ConfigModel(LinkerConfigModel):
    """Base configuration model for linker definitions.

    This class defines the configuration structure used to instantiate
    a specific linking strategy. Each concrete implementation of a
    `LatticeElementsLinker` may define its own subclass extending this model
    to include additional configuration parameters.

    Attributes
    ----------
    model_config : ConfigDict
        Pydantic configuration allowing arbitrary field types and forbidding
        unexpected extra keys.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True,extra="forbid")
    attribute_name: str


class PyAtAttributeIdentifier(LinkerIdentifier):
    """Abstract base class for identifiers used to match PyAML and PyAT elements.

    The identifier acts as an intermediate representation between the PyAML
    configuration and the PyAT lattice. Its exact structure depends on the
    linking strategy (e.g., family name, element index, or user-defined tag).

    Subclasses should define the fields and logic necessary to represent
    a unique reference to one or more PyAT elements.
    """

    def __init__(self, attribute_name:str, identifier):
        self.attribute_name = attribute_name
        self.identifier = identifier

    def __repr__(self):
        return f"{self.attribute_name}={self.identifier}"


class PyAtAttributeElementsLinker(LatticeElementsLinker):
    """Abstract base class defining the interface for PyAT–PyAML element linking.

    Implementations of this class define how PyAML elements are matched
    to PyAT elements based on a given linking strategy (e.g., by family name,
    by index, or by a custom attribute).

    Parameters
    ----------
    config_model : ConfigModel
        The configuration model for the linking strategy.
    """

    def __init__(self, config_model:ConfigModel):
        super().__init__(config_model)

    def get_element_identifier(self, element: Element) -> LinkerIdentifier:
        return PyAtAttributeIdentifier(self.linker_config_model.attribute_name, element.get_name())

    def _test_at_element(self, identifier: PyAtAttributeIdentifier, element: at.Element) -> bool:
        attr_value = getattr(element, identifier.attribute_name, None)
        return attr_value == identifier.identifier
