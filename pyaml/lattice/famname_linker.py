import at
from pydantic import ConfigDict

from pyaml.lattice.element import Element
from pyaml.lattice.lattice_elements_linker import LinkerIdentifier, LinkerConfigModel, LatticeElementsLinker

PYAMLCLASS = "FamNameElementsLinker"


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


class FamNameIdentifier(LinkerIdentifier):
    """Abstract base class for identifiers used to match PyAML and PyAT elements.

    The identifier acts as an intermediate representation between the PyAML
    configuration and the PyAT lattice. Its exact structure depends on the
    linking strategy (e.g., family name, element index, or user-defined tag).

    Subclasses should define the fields and logic necessary to represent
    a unique reference to one or more PyAT elements.
    """

    def __init__(self, family_name:str):
        self.family_name = family_name

    def __repr__(self):
        return f"FamName={self.family_name}"


class FamNameElementsLinker(LatticeElementsLinker):
    """Abstract base class defining the interface for PyAT–PyAML element linking.

    Implementations of this class define how PyAML elements are matched
    to PyAT elements based on a given linking strategy (e.g., by family name,
    by index, or by a custom attribute).

    Parameters
    ----------
    config_model : ConfigModel
        The configuration model for the linking strategy.
    """

    def get_element_identifier(self, element: Element) -> LinkerIdentifier:
        return FamNameIdentifier(element.name)

    def __init__(self, config_model:ConfigModel = None):
        super().__init__(config_model if config_model else ConfigModel())


    def _test_at_element(self, identifier: FamNameIdentifier, element: at.Element) -> bool:
        return element.FamName == identifier.family_name
